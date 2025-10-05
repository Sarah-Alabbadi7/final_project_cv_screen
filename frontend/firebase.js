// frontend/firebase.js
// Shared Firebase init + tiny helper API for both login.html and index.html

(function () {
  // 👉 Fill with your project’s config (Firebase Console → Project settings → Web app)
  const FIREBASE_CONFIG = {
    apiKey:        "AIzaSyBU3W41QoplQ1XuJbB-Q7K8qHmG-v5eeE0",
    authDomain:    "cv-screening-40a27.firebaseapp.com",
    projectId:     "cv-screening-40a27",
    appId:         "1:694775477157:web:2bfa3934cd74a646b42e4c"
    // (optional) storageBucket, messagingSenderId, etc.
  };

  if (!firebase.apps.length) firebase.initializeApp(FIREBASE_CONFIG);

  const auth = firebase.auth();
  // Persist login across tabs/reloads
  auth.setPersistence(firebase.auth.Auth.Persistence.LOCAL);

  // Small helper API exposed on window.fb
  async function getIdToken() {
    const u = auth.currentUser;
    return u ? await u.getIdToken() : null;
  }

  // Require a signed-in user; if none, redirect to login.html
  function requireAuth(redirectTo = 'login.html') {
    return new Promise((resolve) => {
      const unsub = auth.onAuthStateChanged((user) => {
        if (!user) {
          unsub();
          window.location.href = redirectTo;
        } else {
          unsub();
          resolve(user);
        }
      });
    });
  }

  async function signOut() {
    await auth.signOut();
    window.location.href = 'login.html';
  }

  window.fb = { auth, getIdToken, requireAuth, signOut };
})();
