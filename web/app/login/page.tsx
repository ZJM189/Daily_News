import { Suspense } from "react";
import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="loginPage">
          <section className="loginPanel">
            <div className="spinner" />
          </section>
        </main>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
