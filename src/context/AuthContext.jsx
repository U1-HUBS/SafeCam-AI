import React, { createContext, useContext, useState, useEffect, useRef } from "react";
  import authService from "../services/authService";

  const AuthContext = createContext(null);

  export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [userProfile, setUserProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const isRegisteringRef = useRef(false);

    useEffect(() => {
      // Subscribe to Firebase Authentication State Changes
      const unsubscribe = authService.subscribeToAuthState(({ user: fbUser, userProfile: profile }) => {
        if (!isRegisteringRef.current) {
          setUser(fbUser);
          setUserProfile(profile);
        }
        setLoading(false);
      });

      return () => unsubscribe();
    }, []);

    const login = async (email, password) => {
      const res = await authService.loginUser(email, password);
      setUser(res.user);
      setUserProfile(res.userProfile);
      return res;
    };

    const register = async (fullName, email, password) => {
      isRegisteringRef.current = true;
      try {
        const res = await authService.registerUser(fullName, email, password);
        // Registration creates account and signs out temporary session per workflow requirements
        setUser(null);
        setUserProfile(null);
        return res;
      } finally {
        isRegisteringRef.current = false;
      }
    };

    const resetPassword = async (email) => {
      return await authService.sendPasswordReset(email);
    };

    const logout = async () => {
      setLoading(true);
      try {
        await authService.logoutUser();
        setUser(null);
        setUserProfile(null);
      } finally {
        setLoading(false);
      }
    };

    return (
      <AuthContext.Provider
        value={{
          user,
          userProfile,
          loading,
          isAuthenticated: Boolean(user),
          login,
          register,
          resetPassword,
          logout
        }}
      >
        {children}
      </AuthContext.Provider>
    );
  };

  export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
      throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
  };

  export default AuthContext;
