"use client";

import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  name?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary — prevents a single panel crash from taking down the entire dashboard.
 * Wraps each panel component independently.
 */
export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error) {
    console.error(`[ErrorBoundary:${this.props.name || "unknown"}]`, error.message);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="h-full flex flex-col items-center justify-center p-4 text-center">
            <p className="text-xs text-slate-500 mb-1">
              ⚠️ {this.props.name || "Panel"} error
            </p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="text-[10px] text-cyan-400 hover:underline"
            >
              Retry
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
