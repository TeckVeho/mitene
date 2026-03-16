import confetti from "canvas-confetti";

type AnimationFn = () => void;

const animations: AnimationFn[] = [
  // 1. クラシック紙吹雪
  () => {
    confetti({
      particleCount: 150,
      spread: 80,
      origin: { y: 0.6 },
      colors: ["#22c55e", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6"],
    });
  },

  // 2. 花火（左右から連続発射）
  () => {
    const duration = 1500;
    const end = Date.now() + duration;

    (function frame() {
      confetti({
        particleCount: 3,
        angle: 60,
        spread: 55,
        origin: { x: 0 },
        colors: ["#ef4444", "#f59e0b", "#22c55e"],
      });
      confetti({
        particleCount: 3,
        angle: 120,
        spread: 55,
        origin: { x: 1 },
        colors: ["#3b82f6", "#8b5cf6", "#ec4899"],
      });

      if (Date.now() < end) {
        requestAnimationFrame(frame);
      }
    })();
  },

  // 3. 雪（上からふわふわ）
  () => {
    confetti({
      particleCount: 100,
      spread: 100,
      origin: { y: 0 },
      colors: ["#ffffff", "#e0e7ff", "#fef3c7", "#d1fae5"],
      shapes: ["circle"],
      scalar: 0.8,
      gravity: 0.3,
      drift: 0.5,
    });
  },

  // 4. 中央からスターバースト
  () => {
    confetti({
      particleCount: 200,
      spread: 360,
      origin: { x: 0.5, y: 0.5 },
      colors: ["#22c55e", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"],
      shapes: ["circle", "square", "star"],
    });
  },

  // 5. 左右カノン
  () => {
    const count = 80;
    const defaults = { origin: { y: 0.7 } };

    function fire(particleRatio: number, opts: confetti.Options) {
      confetti({
        ...defaults,
        ...opts,
        particleCount: Math.floor(count * particleRatio),
      });
    }

    fire(0.25, { spread: 26, startVelocity: 55, colors: ["#22c55e", "#3b82f6"] });
    fire(0.2, { spread: 60, colors: ["#f59e0b", "#ef4444"] });
    fire(0.35, { spread: 100, decay: 0.91, scalar: 0.8, colors: ["#8b5cf6", "#ec4899"] });
    fire(0.1, { spread: 120, startVelocity: 25, decay: 0.92, scalar: 1.2 });
    fire(0.1, { spread: 120, startVelocity: 45, colors: ["#22c55e"] });
  },

  // 6. 下から打ち上げ
  () => {
    const scalar = 2;
    const star = confetti.shapeFromText({ text: "★", scalar });
    const circle = confetti.shapeFromText({ text: "●", scalar });

    confetti({
      particleCount: 80,
      spread: 70,
      origin: { y: 0.8 },
      shapes: [star, circle],
      colors: ["#fbbf24", "#f59e0b", "#ef4444", "#ec4899"],
    });
  },

  // 7. 虹色グラデーション
  () => {
    confetti({
      particleCount: 120,
      spread: 100,
      origin: { y: 0.5 },
      colors: ["#ef4444", "#f97316", "#eab308", "#22c55e", "#3b82f6", "#8b5cf6", "#ec4899"],
      shapes: ["circle", "square"],
      scalar: 1.2,
    });
  },

  // 8. エモジ紙吹雪
  () => {
    const shapes = [
      confetti.shapeFromText({ text: "🎉", scalar: 0.8 }),
      confetti.shapeFromText({ text: "✓", scalar: 0.6 }),
      confetti.shapeFromText({ text: "⭐", scalar: 0.7 }),
    ];

    confetti({
      particleCount: 60,
      spread: 90,
      origin: { y: 0.6 },
      shapes,
    });
  },

  // 9. 控えめな上昇
  () => {
    confetti({
      particleCount: 80,
      spread: 60,
      origin: { y: 0.7 },
      startVelocity: 30,
      colors: ["#22c55e", "#10b981", "#34d399"],
      shapes: ["circle"],
      scalar: 0.9,
    });
  },

  // 10. パーティークラッカー（左右から）
  () => {
    setTimeout(() => {
      confetti({
        particleCount: 100,
        angle: 60,
        spread: 55,
        origin: { x: 0, y: 0.7 },
        colors: ["#22c55e", "#3b82f6", "#f59e0b"],
      });
    }, 0);
    setTimeout(() => {
      confetti({
        particleCount: 100,
        angle: 120,
        spread: 55,
        origin: { x: 1, y: 0.7 },
        colors: ["#ef4444", "#8b5cf6", "#ec4899"],
      });
    }, 150);
  },
];

export function playRandomCelebration(): void {
  const index = Math.floor(Math.random() * animations.length);
  animations[index]();
}
