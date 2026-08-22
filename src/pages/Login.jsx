import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ShieldAlert, Mail, Lock, LogIn, ArrowRight, AlertTriangle, UserPlus, ExternalLink } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { getAuthErrorMessage } from "../services/authService";
import Input from "../components/ui/Input";
import Button from "../components/ui/Button";

export const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState({});
  const [generalError, setGeneralError] = useState(null); // string or object
  const [isLoading, setIsLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const validate = () => {
    const errs = {};
    if (!email.trim()) errs.email = "Email address is required.";
    else if (!/\S+@\S+\.\S+/.test(email)) errs.email = "Please enter a valid email address.";
    if (!password) errs.password = "Password is required.";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setGeneralError(null);
    if (!validate()) return;

    setIsLoading(true);
    try {
      await login(email.trim(), password);
      navigate("/");
    } catch (err) {
      console.error("Login error:", err);
      setGeneralError(getAuthErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B1120] flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[#00D4FF]/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[#00D4FF]/5 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md glass-card rounded-2xl p-8 border border-[#00D4FF]/30 glow-cyan relative z-10"
      >
        {/* Brand Logo & Title */}
        <div className="text-center space-y-2 mb-8">
          <div className="inline-flex p-3 rounded-2xl bg-[#00D4FF]/10 text-[#00D4FF] border border-[#00D4FF]/30 glow-cyan mb-2">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-black tracking-tight text-[#F8FAFC]">
            SAFECAM <span className="text-[#00D4FF]">AI</span>
          </h1>
          <p className="text-xs font-mono font-bold tracking-widest uppercase text-[#94A3B8]">
            AI BULLYING DETECTION
          </p>
        </div>

        {/* Firebase Authentication Error Banner */}
        {generalError && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 rounded-xl bg-[#EF4444]/15 border border-[#EF4444]/40 text-xs text-[#EF4444] space-y-2 font-mono"
          >
            <div className="flex items-center gap-2 font-bold uppercase tracking-wider">
              <AlertTriangle className="w-4 h-4 shrink-0 text-[#EF4444]" />
              <span>AUTHENTICATION ERROR</span>
            </div>
            <p className="font-sans text-[#F8FAFC] leading-relaxed">
              {typeof generalError === "string" ? generalError : generalError.message}
            </p>
          </motion.div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <Input
            label="Security Email"
            type="email"
            placeholder="user@gmail.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={errors.email}
            icon={Mail}
            required
          />

          <div>
            <Input
              label="Account Password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={errors.password}
              icon={Lock}
              isPassword
              required
            />
            <div className="flex justify-end mt-2">
              <Link
                to="/forgot-password"
                className="text-xs text-[#00D4FF] hover:underline font-medium"
              >
                Forgot Password?
              </Link>
            </div>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            isLoading={isLoading}
            className="w-full mt-2 font-bold"
            icon={LogIn}
          >
            {isLoading ? "AUTHENTICATING..." : "SIGN IN"}
          </Button>
        </form>

        {/* Footer Link to Register */}
        <div className="mt-8 pt-6 border-t border-white/10 text-center text-xs text-[#94A3B8]">
          Don't have an account?{" "}
          <Link to="/register" className="text-[#00D4FF] font-semibold hover:underline inline-flex items-center gap-1">
            Register Account <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </motion.div>
    </div>
  );
};

export default Login;
