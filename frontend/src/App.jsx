// frontend/src/App.jsx
import { useState } from "react";
import reactLogo from "./assets/react.svg";
import viteLogo from "/vite.svg";
import "./App.css";

// Clerk prebuilt components
import {
  SignedIn,
  SignedOut,
  SignInButton,
  SignUpButton,
  UserButton,
} from "@clerk/clerk-react";

function App() {
  const [count, setCount] = useState(0);

  return (
    <>
      <header style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
        <SignedOut>
          <SignInButton mode="modal" />
          <SignUpButton mode="modal" />
        </SignedOut>

        <SignedIn>
          <UserButton />
          <span style={{ marginLeft: "0.5rem" }}>✅ Signed in</span>
        </SignedIn>
      </header>

      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>

      <h1>Vite + React + Clerk</h1>

      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
        <p>
          Edit <code>src/App.jsx</code> and save to test HMR
        </p>
      </div>

      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
    </>
  );
}

export default App;
