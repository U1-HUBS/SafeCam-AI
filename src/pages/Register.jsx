import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ShieldAlert, User, Mail, Lock, UserPlus, CheckCircle2, ArrowRight, AlertTriangle, LogIn, ExternalLink } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import Input from "../components/ui/Input";
import Button from "../components/ui/Button";

export const Register = () => {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState({});
  const [generalError, setGeneralError] = useState(null); // { type, title, message }
  const [isSuccess, setIsSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [countdown, setCountdown] = useState(2);

  const { register } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isSuccess) return;

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          navigate("/login");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isSuccess, navigate]);

  // Password strength helper
  const getPasswordStrength = (pwd) => {
    if (!pwd) return { score: 0, label: "Empty", color: "bg-slate-700" };
    let score = 0;
    if (pwd.length >= 8) score++;
    if (/[A-Z]/.test(pwd)) score++;
    if (/[0-9]/.test(pwd)) score++;
    if (/[^A-Za-z0-9]/.test(pwd)) score++;

    switch (score) {
      case 1:
        return { score: 25, label: "Weak", color: "bg-[#EF4444]" };
      case 2:
        return { score: 50, label: "Medium", color: "bg-amber-400" };
      case 3:
        return { score: 75, label: "Strong", color: "bg-[#00D4FF]" };
      case 4:
        return { score: 100, label: "Tactical Grade", color: "bg-[#00D4FF]" };
      default:
        return { score: 15, label: "Too Short", color: "bg-[#EF4444]" };
    }
  };

  const strength = getPasswordStrength(password);

  const validate = () => {
    const errs = {};
    if (!fullName.trim()) errs.fullName = "Full Name is required.";
    if (!email.trim()) errs.email = "Email is required.";
    else if (!/\S+@\S+\.\S+/.test(email)) errs.email = "Please enter a valid email address.";
    if (!password) errs.password = "Password is required.";
    else if (password.length < 6) errs.password = "Password must be at least 6 characters.";
    if (password !== confirmPassword) errs.confirmPassword = "Passwords do not match.";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setGeneralError(null);
    if (!validate()) return;

    setIsLoading(true);
    try {
      await register(fullName, email.trim(), password);
      setIsSuccess(true);
    } catch (err) {
      setGeneralError({
        type: err.authType || "ERROR",
        title: err.title || "REGISTRATION FAILED",
        message: err.message || "Failed to create security account."
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B1120] flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-[#00D4FF]/5 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md glass-card rounded-2xl p-8 border border-white/10 relative z-10"
      >
        <div className="text-center space-y-2 mb-6">
          <div className="inline-flex p-3 rounded-2xl bg-[#00D4FF]/10 text-[#00D4FF] border border-[#00D4FF]/30 glow-cyan mb-2">
            <ShieldAlert className="w-7 h-7" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[#F8FAFC]">
            Create User Account
          </h1>
          <p className="text-xs text-[#94A3B8]">
            Register to gain access to live surveillance telemetry
          </p>
        </div>

        {/* REGISTRATION SUCCESS VIEW */}
        {isSuccess ? (
          <div className="space-y-6 text-center py-4">
            <div className="p-6 rounded-2xl bg-[#00D4FF]/10 border border-[#00D4FF]/30 space-y-3">
              <CheckCircle2 className="w-12 h-12 text-[#00D4FF] mx-auto animate-bounce" />
              <h2 className="text-lg font-extrabold text-white tracking-tight">ACCOUNT CREATED</h2>
              <p className="text-xs text-[#94A3B8] font-sans leading-relaxed">
                Your SAFECAM AI account has been created successfully. Redirecting to login in <span className="font-bold text-[#00D4FF]">{countdown}s</span>...
              </p>
            </div>

            <Button
              variant="primary"
              size="lg"
              className="w-full"
              icon={ArrowRight}
              onClick={() => navigate("/login")}
            >
              CONTINUE TO LOGIN ({countdown}s)
            </Button>
          </div>
        ) : (
          /* REGISTRATION FORM */
          <>
            {/* Duplicate Email or Firebase Configuration Error Alert */}
            {generalError && (
              <div className="mb-5 p-4 rounded-xl bg-[#EF4444]/15 border border-[#EF4444]/40 text-xs text-[#EF4444] space-y-2">
                <div className="flex items-center gap-2 font-bold uppercase tracking-wider">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{generalError.title}</span>
                </div>
                <p className="font-sans leading-relaxed text-[#F8FAFC]">
                  {generalError.message}
                </p>

                {/* Operation Not Allowed CTA Button to Firebase Console */}
                {generalError.type === "OPERATION_NOT_ALLOWED" && (
                  <div className="pt-2">
                    <a
                      href="https://console.firebase.google.com/u/0/project/safecam-ai/authentication/providers"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-[#00D4FF] text-slate-950 font-bold text-xs hover:bg-[#00D4FF]/90 transition-colors shadow-lg"
                    >
                      <span>OPEN FIREBASE CONSOLE SIGN-IN TAB</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                )}

                {/* Duplicate Email / Gmail CTA Button */}
                {generalError.type === "DUPLICATE_EMAIL" && (
                  <div className="pt-2">
                    <Button
                      type="button"
                      variant="primary"
                      size="sm"
                      icon={LogIn}
                      onClick={() => navigate("/login")}
                      className="w-full text-xs py-2 font-bold"
                    >
                      SIGN IN TO EXISTING ACCOUNT
                    </Button>
                  </div>
                )}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Full Name"
                placeholder="Alex Vance"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                error={errors.fullName}
                icon={User}
                required
              />

              <Input
                label="Email Address (Gmail)"
                type="email"
                placeholder="vance@gmail.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                error={errors.email}
                icon={Mail}
                required
              />

              <div>
                <Input
                  label="Password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  error={errors.password}
                  icon={Lock}
                  isPassword
                  required
                />
                {password && (
                  <div className="mt-2 space-y-1">
                    <div className="flex justify-between items-center text-[10px] font-mono">
                      <span className="text-[#94A3B8]">Strength:</span>
                      <span className="font-bold text-white uppercase">{strength.label}</span>
                    </div>
                    <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                      <div className={`h-full ${strength.color} transition-all duration-300`} style={{ width: `${strength.score}%` }} />
                    </div>
                  </div>
                )}
              </div>

              <Input
                label="Confirm Password"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                error={errors.confirmPassword}
                icon={Lock}
                isPassword
                required
              />

              <Button
                type="submit"
                variant="secondary"
                size="lg"
                isLoading={isLoading}
                className="w-full mt-2 font-bold"
                icon={UserPlus}
              >
                {isLoading ? "CREATING ACCOUNT..." : "CREATE ACCOUNT"}
              </Button>
            </form>

            <div className="mt-6 pt-4 border-t border-white/10 text-center text-xs text-[#94A3B8]">
              Already registered?{" "}
              <Link to="/login" className="text-[#00D4FF] font-semibold hover:underline">
                Sign In Here
              </Link>
            </div>
          </>
        )}
      </motion.div>
    </div>
  );
};

export default Register;
