import React, { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { KeyRound, Mail, CheckCircle2, ArrowLeft, AlertTriangle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import Input from "../components/ui/Input";
import Button from "../components/ui/Button";

export const ForgotPassword = () => {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const { resetPassword } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!email.trim() || !/\S+@\S+\.\S+/.test(email)) {
      setError("Please enter a valid security email address.");
      return;
    }

    setIsLoading(true);
    try {
      await resetPassword(email.trim());
      setIsSuccess(true);
    } catch (err) {
      setError(err.message || "Failed to send password reset email.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B1120] flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-1/3 left-1/3 w-96 h-96 bg-[#00D4FF]/10 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md glass-card rounded-2xl p-8 border border-white/10 relative z-10"
      >
        <div className="text-center space-y-2 mb-6">
          <div className="inline-flex p-3 rounded-2xl bg-[#00D4FF]/10 text-[#00D4FF] border border-[#00D4FF]/30 glow-cyan mb-2">
            <KeyRound className="w-7 h-7" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[#F8FAFC]">
            Forgot your password?
          </h1>
          <p className="text-xs text-[#94A3B8]">
            Enter your registered security email to receive Firebase reset instructions.
          </p>
        </div>

        {/* RESET EMAIL SENT SUCCESS VIEW per Specification #15 */}
        {isSuccess ? (
          <div className="space-y-6 text-center py-2">
            <div className="p-6 rounded-2xl bg-[#00D4FF]/10 border border-[#00D4FF]/30 space-y-3">
              <CheckCircle2 className="w-12 h-12 text-[#00D4FF] mx-auto" />
              <h2 className="text-lg font-extrabold text-white tracking-tight">RESET EMAIL SENT</h2>
              <p className="text-xs text-[#94A3B8] font-sans leading-relaxed">
                Check your email inbox ({email}) for the password reset instructions sent by Firebase Authentication.
              </p>
            </div>

            <Link to="/login" className="block w-full">
              <Button variant="outline" className="w-full" icon={ArrowLeft}>
                Back to Sign In
              </Button>
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="p-3.5 rounded-xl bg-[#EF4444]/15 border border-[#EF4444]/40 text-xs text-[#EF4444] font-medium flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <Input
              label="Security Email"
              type="email"
              placeholder="user@safecam.ai"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              icon={Mail}
              required
            />

            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isLoading}
              className="w-full"
            >
              Send Password Reset Email
            </Button>

            <div className="pt-2 text-center">
              <Link to="/login" className="text-xs text-[#94A3B8] hover:text-white inline-flex items-center gap-1 font-medium">
                <ArrowLeft className="w-3.5 h-3.5" /> Back to Login
              </Link>
            </div>
          </form>
        )}
      </motion.div>
    </div>
  );
};

export default ForgotPassword;
