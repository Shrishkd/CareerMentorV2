import { Component, type ReactNode } from "react";

interface State {
  error: Error | null;
}

/** Shows a recovery screen instead of a blank page if a page crashes while rendering. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error) {
    console.error("Page crashed:", error);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
        <h1 className="text-2xl font-bold">Something went wrong on this page</h1>
        <p className="max-w-md text-muted-foreground">{this.state.error.message}</p>
        <div className="flex gap-3">
          <button
            onClick={() => window.location.reload()}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            Reload page
          </button>
          <a href="/" className="rounded-lg border px-4 py-2 text-sm font-medium">
            Go home
          </a>
        </div>
      </div>
    );
  }
}
