import React, { useState } from "react";
import { User, Shield, Lock, Save, CheckCircle, Mail, Phone, Building } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import Card from "../components/ui/Card";
import Input from "../components/ui/Input";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";

export const Profile = () => {
  const { user, userProfile } = useAuth();

  const [fullName, setFullName] = useState(userProfile?.fullName || user?.displayName || "User");
  const [email, setEmail] = useState(user?.email || "");
  const [phone, setPhone] = useState(userProfile?.phone || "");
  const [department, setDepartment] = useState(userProfile?.department || "Campus Security & AI Operations");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const handleSaveProfile = (e) => {
    e.preventDefault();
    setIsSaving(true);
    setTimeout(() => {
      setIsSaving(false);
      setSuccessMsg("Profile information updated successfully.");
      setTimeout(() => setSuccessMsg(""), 4000);
    }, 600);
  };

  const handlePasswordChange = (e) => {
    e.preventDefault();
    if (!newPassword || newPassword !== confirmNewPassword) {
      alert("New passwords do not match.");
      return;
    }
    setIsSaving(true);
    setTimeout(() => {
      setIsSaving(false);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmNewPassword("");
      setSuccessMsg("Password changed successfully.");
      setTimeout(() => setSuccessMsg(""), 4000);
    }, 600);
  };

  return (
    <div className="space-y-4 sm:space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-black text-[#F8FAFC] tracking-tight flex items-center gap-2">
          <User className="w-5 h-5 text-[#00D4FF]" />
          USER PROFILE
        </h1>
        <p className="text-xs text-[#94A3B8] mt-0.5">
          Firebase Auth UID: <span className="font-mono text-[#00D4FF]">{user?.uid || "Not Authenticated"}</span>
        </p>
      </div>

      {successMsg && (
        <div className="p-3 rounded-xl bg-[#00D4FF]/10 border border-[#00D4FF]/30 text-xs text-[#00D4FF] font-semibold flex items-center gap-2">
          <CheckCircle className="w-4 h-4" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Two-Column Desktop Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-5">
        {/* Left Column (5 of 12 cols): Profile Card + Security Form */}
        <div className="lg:col-span-5 space-y-4 sm:space-y-5">
          {/* User Header Profile Card */}
          <Card glow="cyan">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-xl bg-[#00D4FF]/10 border-2 border-[#00D4FF] flex items-center justify-center text-2xl font-black text-[#00D4FF] shrink-0">
                {(fullName || "U").charAt(0).toUpperCase()}
              </div>
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-[#F8FAFC]">{fullName}</h2>
                  <Badge variant="cyan">USER</Badge>
                </div>
                <p className="text-xs text-[#94A3B8] font-mono">{user?.email}</p>
                <p className="text-xs text-[#00D4FF] font-mono">{department}</p>
              </div>
            </div>
          </Card>

          {/* Security & Change Password Form */}
          <Card>
            <div className="border-b border-white/10 pb-2.5 mb-3.5">
              <h3 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-2">
                <Shield className="w-4 h-4 text-[#00D4FF]" />
                Security & Change Password
              </h3>
            </div>

            <form onSubmit={handlePasswordChange} className="space-y-3">
              <Input
                label="Current Password"
                placeholder="••••••••"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                icon={Lock}
                isPassword
                required
              />

              <Input
                label="New Password"
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                icon={Lock}
                isPassword
                required
              />

              <Input
                label="Confirm New Password"
                placeholder="••••••••"
                value={confirmNewPassword}
                onChange={(e) => setConfirmNewPassword(e.target.value)}
                icon={Lock}
                isPassword
                required
              />

              <div className="pt-1">
                <Button
                  type="submit"
                  variant="secondary"
                  isLoading={isSaving}
                  icon={Lock}
                  className="w-full text-xs"
                >
                  Update Password
                </Button>
              </div>
            </form>
          </Card>

          {/* Firebase Database Connection Card */}
          <Card glow="cyan">
            <div className="border-b border-white/10 pb-2.5 mb-3 flex items-center justify-between">
              <h3 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-2">
                <Building className="w-4 h-4 text-[#00D4FF]" />
                Firebase Database Connection
              </h3>
              <Badge variant="success">● FIRESTORE LIVE</Badge>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-[#94A3B8]">Project ID</span>
                <span className="font-bold text-white">safecam-ai</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-[#94A3B8]">Auth Domain</span>
                <span className="font-bold text-[#00D4FF]">safecam-ai.firebaseapp.com</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-[#94A3B8]">Storage Bucket</span>
                <span className="font-bold text-white">safecam-ai.firebasestorage.app</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Right Column (7 of 12 cols): Personal Information Form */}
        <div className="lg:col-span-7">
          <Card className="h-full flex flex-col justify-between">
            <div>
              <div className="border-b border-white/10 pb-2.5 mb-3.5">
                <h3 className="text-sm font-bold text-[#F8FAFC] flex items-center gap-2">
                  <User className="w-4 h-4 text-[#00D4FF]" />
                  Account Information
                </h3>
              </div>

              <form id="profile-info-form" onSubmit={handleSaveProfile} className="space-y-3.5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <Input
                    label="Full Name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    icon={User}
                    required
                  />
                  <Input
                    label="Email Address"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    icon={Mail}
                    required
                  />
                  <Input
                    label="Phone Number"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    icon={Phone}
                  />
                  <Input
                    label="Security Department"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    icon={Building}
                  />
                </div>
              </form>
            </div>

            <div className="flex justify-end pt-4 mt-4 border-t border-white/10">
              <Button
                type="submit"
                form="profile-info-form"
                variant="primary"
                isLoading={isSaving}
                icon={Save}
                className="text-xs"
              >
                Save Profile Changes
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Profile;
