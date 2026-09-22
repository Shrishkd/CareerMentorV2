"""
QLoRA fine-tune of Qwen3-4B-Instruct on Career Mentor data, exported to GGUF for Ollama.

Needs an NVIDIA GPU (a free Google Colab or Kaggle T4 is enough, ~20-40 min for a
few hundred examples). It will not run on a laptop without CUDA.

On Colab:
    !pip install unsloth
    # upload data/finetune/train.jsonl (and val.jsonl) next to this script
    !python train_qlora.py --epochs 2

Then download career-mentor-gguf/*.gguf, put it in finetune/, and see Modelfile.
"""
import argparse

from datasets import load_dataset
from trl import SFTConfig, SFTTrainer
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template, train_on_responses_only

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="unsloth/Qwen3-4B-Instruct-2507")
ap.add_argument("--train", default="train.jsonl")
ap.add_argument("--val", default="val.jsonl")
ap.add_argument("--epochs", type=float, default=2)
ap.add_argument("--lr", type=float, default=2e-4)
ap.add_argument("--rank", type=int, default=16)
ap.add_argument("--max-len", type=int, default=4096)
ap.add_argument("--out", default="career-mentor-gguf")
args = ap.parse_args()

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=args.base, max_seq_length=args.max_len, load_in_4bit=True,
)
model = FastLanguageModel.get_peft_model(
    model,
    r=args.rank,
    lora_alpha=args.rank,
    lora_dropout=0,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    use_gradient_checkpointing="unsloth",
    random_state=3407,
)
tokenizer = get_chat_template(tokenizer, chat_template="qwen3-instruct")

files = {"train": args.train}
try:
    open(args.val).close()
    files["validation"] = args.val
except OSError:
    pass
data = load_dataset("json", data_files=files)
data = data.map(lambda ex: {"text": tokenizer.apply_chat_template(ex["messages"], tokenize=False)})

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=data["train"],
    eval_dataset=data.get("validation"),
    args=SFTConfig(
        dataset_text_field="text",
        max_seq_length=args.max_len,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=5,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        logging_steps=5,
        eval_strategy="epoch" if "validation" in data else "no",
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        output_dir="outputs",
        report_to="none",
    ),
)
# Only learn the assistant's JSON responses, not the prompts.
trainer = train_on_responses_only(
    trainer, instruction_part="<|im_start|>user\n", response_part="<|im_start|>assistant\n",
)
trainer.train()

model.save_pretrained_gguf(args.out, tokenizer, quantization_method="q4_k_m")
print(f"Saved GGUF to {args.out}/. Copy the .gguf file into finetune/ and run: ollama create career-mentor -f Modelfile")
