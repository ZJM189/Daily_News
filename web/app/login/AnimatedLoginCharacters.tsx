"use client";

import { useEffect, useRef, type CSSProperties } from "react";

type AnimatedLoginCharactersProps = {
  isTyping: boolean;
  showPassword: boolean;
  passwordLength: number;
  loginFailed: boolean;
  loginSuccess: boolean;
};

type CharacterStyle = CSSProperties & Record<`--${string}`, string>;

const confettiColors = ["#ef6c5b", "#2f9f8f", "#f0c75e", "#6d5ce7", "#e88c5a"];

export function AnimatedLoginCharacters({
  isTyping,
  showPassword,
  passwordLength,
  loginFailed,
  loginSuccess
}: AnimatedLoginCharactersProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const characterRefs = useRef<Array<HTMLDivElement | null>>([]);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    let frame = 0;
    let pointerX = window.innerWidth / 2;
    let pointerY = window.innerHeight / 2;

    const clamp = (value: number, min: number, max: number) =>
      Math.max(min, Math.min(max, value));

    const updateCharacters = () => {
      frame = 0;
      characterRefs.current.forEach((character, index) => {
        if (!character) return;
        const rect = character.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 3;
        const x = clamp((pointerX - centerX) / 28, -1, 1);
        const y = clamp((pointerY - centerY) / 32, -1, 1);
        const faceX = x * (index === 0 ? 5 : 7);
        const faceY = y * 4;
        const skew = clamp(-x * 4, -5, 5);

        character.style.setProperty("--face-x", `${faceX}px`);
        character.style.setProperty("--face-y", `${faceY}px`);
        character.style.setProperty("--body-skew", `${skew}deg`);
      });
    };

    const handlePointerMove = (event: PointerEvent) => {
      pointerX = event.clientX;
      pointerY = event.clientY;
      if (!frame) frame = window.requestAnimationFrame(updateCharacters);
    };

    const handleResize = () => {
      if (!frame) frame = window.requestAnimationFrame(updateCharacters);
    };

    window.addEventListener("pointermove", handlePointerMove, { passive: true });
    window.addEventListener("resize", handleResize);
    updateCharacters();

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("resize", handleResize);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, []);

  const rootClassName = [
    "loginCharacters",
    isTyping ? "isTyping" : "",
    showPassword && passwordLength > 0 ? "isShowingPassword" : "",
    loginFailed ? "hasLoginFailed" : "",
    loginSuccess ? "hasLoginSucceeded" : ""
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={rootClassName} ref={rootRef} aria-hidden="true">
      <div className="loginCharacter purpleCharacter" ref={(element) => { characterRefs.current[0] = element; }}>
        <CharacterEyes eyeClassName="lightEyes" />
        <span className="characterMouth purpleMouth" />
      </div>
      <div className="loginCharacter blackCharacter" ref={(element) => { characterRefs.current[1] = element; }}>
        <CharacterEyes eyeClassName="lightEyes" />
        <span className="characterMouth blackMouth" />
      </div>
      <div className="loginCharacter orangeCharacter" ref={(element) => { characterRefs.current[2] = element; }}>
        <CharacterEyes eyeClassName="darkEyes" />
        <span className="characterMouth orangeMouth" />
      </div>
      <div className="loginCharacter yellowCharacter" ref={(element) => { characterRefs.current[3] = element; }}>
        <CharacterEyes eyeClassName="darkEyes" />
        <span className="characterMouth yellowMouth" />
      </div>
      <div className="loginConfetti">
        {Array.from({ length: 28 }, (_, index) => {
          const style: CharacterStyle = {
            "--confetti-x": `${(index * 37) % 100}%`,
            "--confetti-delay": `${(index % 7) * 0.08}s`,
            "--confetti-duration": `${3.2 + (index % 5) * 0.25}s`,
            "--confetti-color": confettiColors[index % confettiColors.length]
          };
          return <span key={index} style={style} />;
        })}
      </div>
    </div>
  );
}

function CharacterEyes({ eyeClassName }: { eyeClassName: string }) {
  return (
    <span className={`characterEyes ${eyeClassName}`}>
      <span className="characterEye">
        <span className="characterPupil" />
      </span>
      <span className="characterEye">
        <span className="characterPupil" />
      </span>
    </span>
  );
}
