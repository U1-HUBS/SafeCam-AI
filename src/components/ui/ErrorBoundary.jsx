import React from "react";
import { AlertOctagon, RefreshCw } from "lucide-react";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error("==========================================");
    console.error("🚨 [REACT COMPONENT ERROR BOUNDARY TRIGGERED]");
    console.error("Error message:", error);
    console.error("Component Stack:", errorInfo ? errorInfo.componentStack : "N/A");
    console.error("==========================================");
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      const componentTitle = this.props.title || "LIVE ALERT COMPONENT ERROR";
      return (
        <div className="w-full p-6 my-4 glass-panel border-2 border-red-500/60 rounded-2xl bg-slate-950 text-white font-mono shadow-2xl">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-xl bg-red-600/20 text-red-400 border border-red-500/40 shrink-0">
              <AlertOctagon className="w-8 h-8 text-red-500 animate-pulse" />
            </div>

            <div className="flex-1 space-y-2">
              <h2 className="text-lg font-black text-red-400 tracking-tight flex items-center gap-2 uppercase">
                🚨 {componentTitle}
              </h2>
              <p className="text-xs text-slate-300">
                A Javascript runtime error occurred while rendering this component. The rest of the SAFECAM dashboard remains fully operational.
              </p>

              <div className="p-3 rounded-lg bg-black/80 border border-red-500/30 text-xs text-red-300 overflow-x-auto font-mono">
                <strong>Exception:</strong> {this.state.error ? this.state.error.toString() : "Unknown Error"}
                {this.state.errorInfo && (
                  <pre className="mt-2 text-[10px] text-slate-400 max-h-40 overflow-y-auto whitespace-pre-wrap">
                    {this.state.errorInfo.componentStack}
                  </pre>
                )}
              </div>

              <div className="pt-2 flex items-center gap-3">
                <button
                  onClick={this.handleRetry}
                  className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-xs shadow-lg transition-all flex items-center gap-2 border border-red-400/40 cursor-pointer"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Retry Component</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
