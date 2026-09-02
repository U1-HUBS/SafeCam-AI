// SAFECAM AI — Firebase Web SDK v12 Integration
import { initializeApp, getApps } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyDummyKeyForSafeCamAILocalDev12345",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "safecam-ai.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "safecam-ai",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "safecam-ai.firebasestorage.app",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "123456789012",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:123456789012:web:abcdef1234567890",
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || "G-XXXXXXXXXX"
};

console.log(
  "[FIREBASE DEBUG] Project:",
  firebaseConfig.projectId
);

// Initialize Firebase App singleton safely
let app;
try {
  app = !getApps().length ? initializeApp(firebaseConfig) : getApps()[0];
} catch (e) {
  console.warn("[FIREBASE DEBUG] initializeApp warning:", e);
}

export const auth = app ? getAuth(app) : null;
export const db = app ? getFirestore(app) : null;
export default app;
