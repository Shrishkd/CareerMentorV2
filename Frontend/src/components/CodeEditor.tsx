import { useState, useRef } from "react";
import { Editor } from "@monaco-editor/react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, Play, Square, Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useToast } from "@/hooks/use-toast";

interface Language {
  id: number;
  name: string;
  extension: string;
  template: string;
}

const languages: Language[] = [
  {
    id: 71,
    name: "Python",
    extension: "py",
    template: `# Python code
def solution():
    # Write your code here
    pass

# Test your solution
if __name__ == "__main__":
    result = solution()
    print(result)`
  },
  {
    id: 63,
    name: "JavaScript",
    extension: "js", 
    template: `// JavaScript code
function solution() {
    // Write your code here
}

// Test your solution
console.log(solution());`
  },
  {
    id: 54,
    name: "C++",
    extension: "cpp",
    template: `#include <iostream>
#include <vector>
#include <string>
using namespace std;

int main() {
    // Write your code here
    
    return 0;
}`
  },
  {
    id: 62,
    name: "Java",
    extension: "java",
    template: `public class Solution {
    public static void main(String[] args) {
        // Write your code here
        
    }
}`
  },
  {
    id: 60,
    name: "Go",
    extension: "go",
    template: `package main

import "fmt"

func main() {
    // Write your code here
    
}`
  }
];

interface CodeEditorProps {
  question?: string;
  onCodeChange?: (code: string) => void;
}

export const CodeEditor = ({ question, onCodeChange }: CodeEditorProps) => {
  const [selectedLanguage, setSelectedLanguage] = useState<Language>(languages[0]);
  const [code, setCode] = useState(selectedLanguage.template);
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [executionTime, setExecutionTime] = useState<number | null>(null);
  const [memory, setMemory] = useState<number | null>(null);
  const editorRef = useRef(null);
  const { toast } = useToast();

  const handleLanguageChange = (languageId: string) => {
    const language = languages.find(lang => lang.id === parseInt(languageId));
    if (language) {
      setSelectedLanguage(language);
      setCode(language.template);
      setOutput("");
      setExecutionTime(null);
      setMemory(null);
    }
  };

  const handleCodeChange = (value: string | undefined) => {
    const newCode = value || "";
    setCode(newCode);
    onCodeChange?.(newCode);
  };

  const executeCode = async () => {
    if (!code.trim()) {
      toast({
        title: "No Code",
        description: "Please write some code before running.",
        variant: "destructive"
      });
      return;
    }

    const rapidApiKey = import.meta.env.VITE_RAPIDAPI_KEY;
    if (!rapidApiKey) {
      setOutput("❌ Error: RapidAPI key not configured. Please set VITE_RAPIDAPI_KEY in your environment variables.");
      toast({
        title: "Configuration Error",
        description: "RapidAPI key is required for code execution. Please contact your administrator.",
        variant: "destructive"
      });
      return;
    }

    setIsRunning(true);
    setOutput("");
    setExecutionTime(null);
    setMemory(null);

    try {
      // Create submission
      const submissionResponse = await fetch("https://judge0-ce.p.rapidapi.com/submissions?base64_encoded=false&wait=true", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-RapidAPI-Key": rapidApiKey,
          "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com"
        },
        body: JSON.stringify({
          language_id: selectedLanguage.id,
          source_code: code,
          stdin: input,
          expected_output: null
        })
      });

      if (!submissionResponse.ok) {
        throw new Error(`HTTP error! status: ${submissionResponse.status}`);
      }

      const result = await submissionResponse.json();
      
      if (result.status?.id === 3) {
        // Successful execution
        setOutput(result.stdout || "No output");
        setExecutionTime(parseFloat(result.time) || 0);
        setMemory(parseInt(result.memory) || 0);
        
        toast({
          title: "Code Executed Successfully",
          description: `Executed in ${result.time}s`
        });
      } else if (result.status?.id === 5) {
        // Time limit exceeded
        setOutput("Error: Time limit exceeded");
        toast({
          title: "Execution Error",
          description: "Time limit exceeded",
          variant: "destructive"
        });
      } else if (result.status?.id === 6) {
        // Compile error
        setOutput(result.compile_output || "Compilation error");
        toast({
          title: "Compilation Error",
          description: "Check your code syntax",
          variant: "destructive"
        });
      } else if (result.stderr) {
        // Runtime error
        setOutput(result.stderr);
        toast({
          title: "Runtime Error",
          description: "Check your code logic",
          variant: "destructive"
        });
      } else {
        setOutput(result.stdout || "No output");
      }
    } catch (error: any) {
      console.error("Execution error:", error);
      let errorMessage = "Unable to execute code. Please try again.";
      
      if (error.message?.includes("401")) {
        errorMessage = "Invalid API key. Please check your RapidAPI key configuration.";
      } else if (error.message?.includes("429")) {
        errorMessage = "Rate limit exceeded. Please try again later.";
      } else if (error.message?.includes("403")) {
        errorMessage = "Access forbidden. Please check your API key permissions.";
      } else if (error.message?.includes("Network")) {
        errorMessage = "Network error. Please check your internet connection.";
      }
      
      setOutput(`❌ Error: ${errorMessage}`);
      toast({
        title: "Execution Failed",
        description: errorMessage,
        variant: "destructive"
      });
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      {question && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Programming Challenge</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-foreground whitespace-pre-wrap">{question}</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle className="text-lg">Code Editor</CardTitle>
          <div className="flex items-center space-x-4">
            <Select value={selectedLanguage.id.toString()} onValueChange={handleLanguageChange}>
              <SelectTrigger className="w-40 bg-muted border-2 border-border hover:border-primary transition-colors">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-popover border-2 border-border">
                {languages.map((lang) => (
                  <SelectItem 
                    key={lang.id} 
                    value={lang.id.toString()}
                    className="hover:bg-accent focus:bg-accent cursor-pointer"
                  >
                    {lang.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button 
              onClick={executeCode} 
              disabled={isRunning}
              className="bg-gradient-primary text-primary-foreground"
            >
              {isRunning ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Running
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Run Code
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="border border-border rounded-lg overflow-hidden">
            <Editor
              height="400px"
              language={selectedLanguage.name.toLowerCase()}
              value={code}
              onChange={handleCodeChange}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 2,
                wordWrap: "on"
              }}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Input (stdin)</label>
              <Textarea
                placeholder="Enter input for your program..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                className="min-h-[100px] font-mono text-sm"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium">Output</label>
                {executionTime !== null && (
                  <div className="flex space-x-2">
                    <Badge variant="secondary" className="text-xs">
                      {executionTime}s
                    </Badge>
                    {memory !== null && (
                      <Badge variant="secondary" className="text-xs">
                        {memory} KB
                      </Badge>
                    )}
                  </div>
                )}
              </div>
              <div className="border border-border rounded-lg p-3 min-h-[100px] bg-muted font-mono text-sm whitespace-pre-wrap">
                {output || "Output will appear here..."}
              </div>
            </div>
          </div>

          {output.includes("Error:") && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                There was an error executing your code. Check the output above for details.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default CodeEditor;