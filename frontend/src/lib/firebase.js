// Firebase configuration for CAT Prep App
// This is a demo configuration - in production, use your own Firebase project

import { initializeApp } from 'firebase/app';
import { getAuth, connectAuthEmulator } from 'firebase/auth';

// Demo Firebase config - replace with your actual config in production
const firebaseConfig = {
  apiKey: "demo-api-key-cat-prep-2025",
  authDomain: "cat-prep-demo.firebaseapp.com",
  projectId: "cat-prep-demo",
  storageBucket: "cat-prep-demo.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:demo-app-id"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Auth
const auth = getAuth(app);

// For development - you can connect to Firebase Auth emulator
if (process.env.NODE_ENV === 'development' && !auth._delegate._config) {
  try {
    connectAuthEmulator(auth, 'http://localhost:9099', { disableWarnings: true });
  } catch (error) {
    // Auth emulator already connected or not available
    console.log('Firebase Auth emulator connection info:', error.message);
  }
}

export { auth };
export default app;