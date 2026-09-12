import { Suspense } from "react";
import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="loginPage">
          <main className="loginMain">
            <section className="loginPanel loginLoadingPanel">
              <div className="spinner" />
            </section>
          </main>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
