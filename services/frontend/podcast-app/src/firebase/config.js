// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyAPqx7bjAe0p7sFrTeNacrwFcVkuQUBewE",
  authDomain: "newsjuice-40a77.firebaseapp.com",
  projectId: "newsjuice-40a77",
  storageBucket: "newsjuice-40a77.firebasestorage.app",
  messagingSenderId: "98363376964",
  appId: "1:98363376964:web:5a4cb7efdc954d52b14311",
  measurementId: "G-V61F0EJL1Y"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Auth
export const auth = getAuth(app);

