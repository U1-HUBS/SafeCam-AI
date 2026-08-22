// SAFECAM AI — Strict Firebase Authentication Service (Web SDK v12)
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  sendPasswordResetEmail, 
  signOut,
  onAuthStateChanged 
} from "firebase/auth";
import { doc, setDoc, getDoc, serverTimestamp } from "firebase/firestore";
import { auth, db } from "./firebase";

export const getAuthErrorMessage = (error) => {
  const code = error?.code || error?.authType || "";
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
  const code = error.code || "";
  const msg = error.message || "";

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
      console.error("🔥 FIREBASE AUTH ERROR CODE:", err.code);
      console.error("🔥 FIREBASE AUTH ERROR MESSAGE:", err.message);
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

    // 2. Attempt Firestore user document persistence
    try {
      const userDocRef = doc(db, "users", user.uid);
      await setDoc(userDocRef, userProfile, { merge: true });
      console.log("[Firestore] User document created in users/", user.uid);
    } catch (firestoreErr) {
      console.warn("[Firestore] User document creation warning:", firestoreErr?.message || firestoreErr);
    }

    // 3. Sign out temporary registration session so user logs in cleanly
    try {
      await signOut(auth);
    } catch (signOutErr) {
      // Ignore signout error
    }

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
    console.log("[Firebase Auth] Attempting login for:", cleanEmail);

    try {
      const userCredential = await signInWithEmailAndPassword(auth, cleanEmail, password);
      const user = userCredential.user;
      console.log("[Firebase Auth] Login successful! UID:", user.uid);

      // Fetch Firestore Profile Document
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
      fullName: auth.currentUser?.displayName || "User",
      email: auth.currentUser?.email || "",
      role: "user"
    };
  },

  // ---------------------------------------------------------------------------
  // 6. CURRENT USER & AUTH STATE LISTENER
  // ---------------------------------------------------------------------------
  getCurrentUser() {
    return auth.currentUser;
  },

  subscribeToAuthState(callback) {
    return onAuthStateChanged(auth, async (user) => {
      if (user) {
        const profile = await this.getUserProfile(user.uid);
        callback({ user, userProfile: profile });
      } else {
        callback({ user: null, userProfile: null });
      }
    });
  }
};

export default authService;
