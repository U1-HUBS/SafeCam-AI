// SAFECAM AI — Strict Firebase & Local Auth Service (Web SDK v12)
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  sendPasswordResetEmail, 
  signOut,
  onAuthStateChanged 
} from "firebase/auth";
import { doc, setDoc, getDoc } from "firebase/firestore";
import { auth, db } from "./firebase";

const isFirebaseEnabled = () => import.meta.env.VITE_USE_FIREBASE === "true";

export const getAuthErrorMessage = (error) => {
  const code = error?.code || error?.authType || "";
  const msg = error?.message || "";

  if (code === "INVALID_API_KEY" || code.includes("api-key") || msg.includes("api-key")) {
    return "Firebase Web API key is invalid or using a placeholder. Please update VITE_FIREBASE_API_KEY in your .env file.";
  }

  switch (code) {
    case "auth/invalid-credential":
    case "auth/user-not-found":
    case "auth/wrong-password":
    case "INVALID_CREDENTIAL":
    case "USER_NOT_FOUND":
    case "WRONG_PASSWORD":
      return "Incorrect email or password.";
    case "auth/invalid-email":
    case "INVALID_EMAIL":
      return "Please enter a valid email address.";
    case "auth/too-many-requests":
    case "TOO_MANY_REQUESTS":
      return "Too many login attempts. Please try again later.";
    case "auth/network-request-failed":
      return "Network error. Please check your internet connection.";
    default:
      return error?.message || "Unable to sign in. Please check your email and password.";
  }
};

export const parseAuthError = (error) => {
  const code = error?.code || "";
  const msg = error?.message || "";

  if (code.includes("api-key") || msg.includes("api-key") || code.includes("invalid-api-key")) {
    return {
      type: "INVALID_API_KEY",
      title: "FIREBASE API KEY INVALID",
      message: "Your Firebase Web API Key in .env is invalid or using a placeholder. Please update VITE_FIREBASE_API_KEY in .env with a valid key from Firebase Console."
    };
  }

  switch (code) {
    case "auth/email-already-in-use":
      return {
        type: "DUPLICATE_EMAIL",
        title: "EMAIL ALREADY REGISTERED",
        message: "This email address is already registered with a SAFECAM AI account. Please sign in instead."
      };
    case "auth/user-not-found":
      return {
        type: "USER_NOT_FOUND",
        title: "ACCOUNT NOT REGISTERED",
        message: "This email address is not registered with SAFECAM AI. Click below to create an account."
      };
    case "auth/wrong-password":
      return {
        type: "WRONG_PASSWORD",
        title: "INCORRECT PASSWORD",
        message: "The password you entered is incorrect. Please double-check your credentials and try again."
      };
    case "auth/invalid-credential":
      return {
        type: "INVALID_CREDENTIAL",
        title: "ACCOUNT NOT REGISTERED OR INCORRECT PASSWORD",
        message: "This email is either not registered or the password entered is incorrect."
      };
    case "auth/operation-not-allowed":
      return {
        type: "OPERATION_NOT_ALLOWED",
        title: "ENABLE EMAIL SIGN-IN IN FIREBASE CONSOLE",
        message: "Email/Password sign-in method is disabled in your Firebase console. Go to Firebase Console > Authentication > Sign-in method tab and enable Email/Password."
      };
    case "auth/invalid-api-key":
    case "auth/api-key-not-valid":
      return {
        type: "INVALID_API_KEY",
        title: "FIREBASE API KEY INVALID",
        message: "Your Firebase Web API Key is invalid or restricted in Google Cloud. Please check Firebase Console > Project Settings."
      };
    case "auth/invalid-email":
      return {
        type: "INVALID_EMAIL",
        title: "INVALID EMAIL ADDRESS",
        message: "Please enter a valid security email address."
      };
    case "auth/weak-password":
      return {
        type: "WEAK_PASSWORD",
        title: "WEAK PASSWORD",
        message: "Password must be at least 6 characters long."
      };
    case "auth/too-many-requests":
      return {
        type: "TOO_MANY_REQUESTS",
        title: "TOO MANY FAILED ATTEMPTS",
        message: "Access temporarily blocked due to multiple failed attempts. Please try again later."
      };
    default:
      return {
        type: "UNKNOWN",
        title: "AUTHENTICATION ERROR",
        message: msg.replace("Firebase: ", "") || "Authentication request failed."
      };
  }
};

export const authService = {
  // ---------------------------------------------------------------------------
  // 1. REGISTER USER
  // ---------------------------------------------------------------------------
  async registerUser(fullName, email, password) {
    const cleanEmail = email.toLowerCase().trim();
    const isoTimestamp = new Date().toISOString();

    if (!isFirebaseEnabled()) {
      console.log("[Local Auth] Registering user locally:", cleanEmail);
      const mockUser = {
        uid: "local-" + Date.now(),
        email: cleanEmail,
        displayName: fullName.trim()
      };
      const userProfile = {
        uid: mockUser.uid,
        fullName: fullName.trim(),
        email: cleanEmail,
        role: "user",
        createdAt: isoTimestamp,
        updatedAt: isoTimestamp
      };

      const users = JSON.parse(localStorage.getItem("safecam_mock_users") || "[]");
      if (users.some(u => u.email === cleanEmail)) {
        const errorObj = new Error("This email address is already registered locally.");
        errorObj.authType = "DUPLICATE_EMAIL";
        errorObj.title = "EMAIL ALREADY REGISTERED";
        throw errorObj;
      }
      users.push({ ...userProfile, password });
      localStorage.setItem("safecam_mock_users", JSON.stringify(users));
      return { success: true, uid: mockUser.uid, userProfile };
    }

    console.log("[Firebase Auth] Submitting user registration to Firebase:", cleanEmail);

    let userCredential;
    try {
      userCredential = await createUserWithEmailAndPassword(
        auth,
        cleanEmail,
        password
      );
      console.log("[Firebase Auth] USER CREATED IN FIREBASE CONSOLE! UID:", userCredential.user.uid);
    } catch (err) {
      console.error("🔥 FIREBASE AUTH ERROR OBJECT:", err);
      const parsed = parseAuthError(err);
      const errorObj = new Error(parsed.message);
      errorObj.authType = parsed.type;
      errorObj.title = parsed.title;
      throw errorObj;
    }

    const user = userCredential.user;

    const userProfile = {
      uid: user.uid,
      fullName: fullName.trim(),
      email: cleanEmail,
      role: "user",
      createdAt: isoTimestamp,
      updatedAt: isoTimestamp
    };

    try {
      const userDocRef = doc(db, "users", user.uid);
      await setDoc(userDocRef, userProfile, { merge: true });
    } catch (firestoreErr) {
      console.warn("[Firestore] User document creation warning:", firestoreErr?.message || firestoreErr);
    }

    try {
      await signOut(auth);
    } catch (signOutErr) {}

    return {
      success: true,
      uid: user.uid,
      userProfile
    };
  },

  // ---------------------------------------------------------------------------
  // 2. LOGIN USER
  // ---------------------------------------------------------------------------
  async loginUser(email, password) {
    const cleanEmail = email.toLowerCase().trim();

    if (!isFirebaseEnabled()) {
      console.log("[Local Auth] Attempting local login for:", cleanEmail);
      let users = JSON.parse(localStorage.getItem("safecam_mock_users") || "[]");

      // Seed default admin account if local user database is empty
      if (users.length === 0) {
        const defaultAdmin = {
          uid: "local-admin",
          fullName: "System Admin",
          email: "admin@safecam.ai",
          password: "admin",
          role: "admin",
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        };
        users = [defaultAdmin];
        localStorage.setItem("safecam_mock_users", JSON.stringify(users));
      }

      const found = users.find(u => u.email === cleanEmail);
      
      if (!found) {
        const errorObj = new Error("This email address is not registered with SAFECAM AI. Click below to create an account.");
        errorObj.authType = "USER_NOT_FOUND";
        errorObj.title = "ACCOUNT NOT REGISTERED";
        throw errorObj;
      }

      if (found.password && found.password !== password) {
        const errorObj = new Error("Incorrect email or password.");
        errorObj.authType = "WRONG_PASSWORD";
        errorObj.title = "INCORRECT PASSWORD";
        throw errorObj;
      }

      const mockUser = {
        uid: found.uid,
        email: found.email,
        displayName: found.fullName
      };

      localStorage.setItem("safecam_mock_session", JSON.stringify({ user: mockUser, userProfile: found }));
      window.dispatchEvent(new Event("safecam_auth_change"));

      return {
        success: true,
        user: mockUser,
        userProfile: found
      };
    }

    console.log("[Firebase Auth] Attempting login for:", cleanEmail);

    try {
      const userCredential = await signInWithEmailAndPassword(auth, cleanEmail, password);
      const user = userCredential.user;
      console.log("[Firebase Auth] Login successful! UID:", user.uid);

      const userProfile = await this.getUserProfile(user.uid);

      return {
        success: true,
        user,
        userProfile
      };
    } catch (err) {
      console.error("[Firebase Auth Error] Login failed:", err?.code, err?.message);

      const parsed = parseAuthError(err);
      const errorObj = new Error(parsed.message);
      errorObj.authType = parsed.type;
      errorObj.title = parsed.title;
      throw errorObj;
    }
  },

  // ---------------------------------------------------------------------------
  // 3. LOGOUT USER
  // ---------------------------------------------------------------------------
  async logoutUser() {
    if (!isFirebaseEnabled()) {
      localStorage.removeItem("safecam_mock_session");
      window.dispatchEvent(new Event("safecam_auth_change"));
      return { success: true };
    }
    try {
      await signOut(auth);
      return { success: true };
    } catch (err) {
      console.error("Firebase Logout Error:", err);
      return { success: true };
    }
  },

  // ---------------------------------------------------------------------------
  // 4. PASSWORD RESET EMAIL
  // ---------------------------------------------------------------------------
  async sendPasswordReset(email) {
    if (!isFirebaseEnabled()) {
      return {
        success: true,
        message: `[Local Mode] Password reset email simulated for ${email}.`
      };
    }
    try {
      await sendPasswordResetEmail(auth, email);
      return {
        success: true,
        message: `Password reset email dispatched to ${email}. Check your inbox for instructions.`
      };
    } catch (err) {
      console.error("Firebase Password Reset Error:", err);
      const parsed = parseAuthError(err);
      throw new Error(parsed.message);
    }
  },

  // ---------------------------------------------------------------------------
  // 5. GET USER PROFILE FROM FIRESTORE
  // ---------------------------------------------------------------------------
  async getUserProfile(uid) {
    if (!uid) return null;
    if (!isFirebaseEnabled()) {
      const session = JSON.parse(localStorage.getItem("safecam_mock_session") || "null");
      return session?.userProfile || null;
    }
    try {
      const docRef = doc(db, "users", uid);
      const docSnap = await getDoc(docRef);
      if (docSnap.exists()) {
        return docSnap.data();
      }
    } catch (err) {
      console.warn("Failed to fetch Firestore user profile:", err);
    }

    return {
      uid,
      fullName: auth?.currentUser?.displayName || "User",
      email: auth?.currentUser?.email || "",
      role: "user"
    };
  },

  // ---------------------------------------------------------------------------
  // 6. CURRENT USER & AUTH STATE LISTENER
  // ---------------------------------------------------------------------------
  getCurrentUser() {
    if (!isFirebaseEnabled()) {
      const session = JSON.parse(localStorage.getItem("safecam_mock_session") || "null");
      return session?.user || null;
    }
    return auth?.currentUser || null;
  },

  subscribeToAuthState(callback) {
    if (!isFirebaseEnabled()) {
      const checkSession = () => {
        const session = JSON.parse(localStorage.getItem("safecam_mock_session") || "null");
        callback({ user: session?.user || null, userProfile: session?.userProfile || null });
      };
      checkSession();
      window.addEventListener("safecam_auth_change", checkSession);
      return () => window.removeEventListener("safecam_auth_change", checkSession);
    }

    if (!auth) {
      callback({ user: null, userProfile: null });
      return () => {};
    }
    try {
      return onAuthStateChanged(
        auth,
        async (user) => {
          try {
            if (user) {
              const profile = await this.getUserProfile(user.uid);
              callback({ user, userProfile: profile });
            } else {
              callback({ user: null, userProfile: null });
            }
          } catch (err) {
            console.warn("Error fetching user profile during auth change:", err);
            callback({ user, userProfile: null });
          }
        },
        (error) => {
          console.warn("Firebase onAuthStateChanged error:", error?.message || error);
          callback({ user: null, userProfile: null });
        }
      );
    } catch (err) {
      console.warn("Failed to subscribe to auth state:", err?.message || err);
      callback({ user: null, userProfile: null });
      return () => {};
    }
  }
};

export default authService;
