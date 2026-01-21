import { useEffect, useState } from "react";
import { motion, useAnimation } from "framer-motion";
import { AgentGridVisualizer } from "./AgentGridVisualizer";

type VisualizerState =
  | "offline"
  | "listening"
  | "idle"
  | "speaking"
  | "thinking";

type GroqAudioVisualizerProps = {
  state: VisualizerState;
  barWidth: number;
  minBarHeight: number;
  maxBarHeight: number;
  accentColor: string;
  accentShade?: number;
  frequencies: Float32Array[] | number[][];
  borderRadius: number;
  gap: number;
};

/*
<AgentVisualizer
          state={animationState}
          volumeBands={userVolumeBands}
          options={{
            animationOptions: { interval: 75, connectingRing: 3 },
            baseStyle: {
              width: '4px',
              height: '4px',
              borderRadius: '1px',
            },
            offStyle: {
              backgroundColor: 'rgba(255, 255, 255, 0.2)',
              transform: 'scale(1)',
            },
            onStyle: {
              backgroundColor: 'rgba(255, 255, 255, 1)',
              boxShadow: '0px 0px 10px 2px rgba(255, 255, 255, 0.4)',
              transform: 'scale(1.25)',
            },
            gridSpacing: '12px',
          }}
        />
*/

export const GroqAudioVisualizer = ({
  state,
  frequencies,
}: GroqAudioVisualizerProps) => {
  const [isTabletOrSmaller, setIsTabletOrSmaller] = useState(false);
  const summedFrequencies = frequencies.map((bandFrequencies) => {
    const sum = (bandFrequencies as number[]).reduce((a, b) => a + b, 0);
    return Math.sqrt(sum / bandFrequencies.length);
  });

  const [thinkingIndex, setThinkingIndex] = useState(
    Math.floor(summedFrequencies.length / 2)
  );
  const [thinkingDirection, setThinkingDirection] = useState<"left" | "right">(
    "right"
  );

  useEffect(() => {
    const handleResize = () => {
      setIsTabletOrSmaller(window.innerWidth < 1024);
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    if (state !== "thinking") {
      setThinkingIndex(Math.floor(summedFrequencies.length / 2));
      return;
    }
    const timeout = setTimeout(() => {
      if (thinkingDirection === "right") {
        if (thinkingIndex === summedFrequencies.length - 1) {
          setThinkingDirection("left");
          setThinkingIndex((prev) => prev - 1);
        } else {
          setThinkingIndex((prev) => prev + 1);
        }
      } else {
        if (thinkingIndex === 0) {
          setThinkingDirection("right");
          setThinkingIndex((prev) => prev + 1);
        } else {
          setThinkingIndex((prev) => prev - 1);
        }
      }
    }, 200);

    return () => clearTimeout(timeout);
  }, [state, summedFrequencies.length, thinkingDirection, thinkingIndex]);

  return (
    <div className="relative">
      <div className="relative z-50">
        <CircleChart
          state={state}
          values={[90, 110, 120, 90]}
          frequencies={summedFrequencies.slice(0, 4)}
          radiusBase={isTabletOrSmaller ? 140 : 200}
        />
      </div>
      <motion.div
        initial={{
          opacity: 0,
        }}
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
        animate={{
          opacity: 1,
        }}
        transition={{
          delay: 1,
          duration: 3,
        }}
      >
        <div
          className="absolute top-0 left-0 w-full h-full z-10"
          style={{
            background:
              "radial-gradient(50% 50% at 50% 50%, rgba(245, 80, 54, 1.0) 20%, rgba(245, 80, 54, 0.9) 40%, rgba(245, 80, 54, 0.0) 60%, rgba(245, 80, 54, 1) 100%)",
            transform: "scale(1.01)",
          }}
        />
        <AgentGridVisualizer
          state={"speaking"}
          volumeBands={summedFrequencies}
          options={{
            animationOptions: { interval: 75, connectingRing: 6 },
            baseStyle: {
              width: "4px",
              height: "4px",
              borderRadius: "2px",
            },
            offStyle: {
              backgroundColor: "rgba(255, 255, 255, 0.5)",
              transform: "scale(1)",
            },
            onStyle: {
              backgroundColor: "rgba(255, 255, 255, 1)",
              transform: "scale(1.25)",
            },
            gridSpacing: "12px",
          }}
        />
      </motion.div>
    </div>
  );
};

const CircleChart = ({
  state,
  values,
  frequencies,
  radiusBase,
}: {
  state: VisualizerState;
  values: number[];
  frequencies: number[];
  radiusBase: number;
}) => {
  const [isActive, setIsActive] = useState(false);
  const [gap, setGap] = useState(15);
  const strokeWidth = 15;
  const averageVolume =
  let averageVolume =
    frequencies.reduce((a, b) => a + b, 0) / frequencies.length;
  if (isNaN(averageVolume)) {
    averageVolume = 0;
  }
  const normalizedVolume = Math.pow(averageVolume, 0.3);
  const numCircles = values.length;
  const size =
    radiusBase * 2 + strokeWidth + (numCircles - 1) * (gap + strokeWidth * 2);

  useEffect(() => {
    if (state !== "offline") {
      setIsActive(true);
      setGap(20);
    } else {
      setIsActive(false);
      setGap(15);
    }
  }, [state, normalizedVolume]);

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      overflow="visible"
    >
      <defs>
        <linearGradient id="orange-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#FFF" />
          <stop offset="20%" stopColor="#FFF" />
          <stop offset="100%" stopColor="#FFF" />
        </linearGradient>
      </defs>
      <motion.circle
        cx={size / 2}
        cy={size / 2}
        r={size * 0.1}
        fill="url(#orange-gradient)"
        animate={{
          r: isActive ? radiusBase * 0.75 : size * 0.18, // Animate between two sizes
          opacity: 1,
        }}
        transition={{
          type: "spring",
          stiffness: 150,
          damping: 13,
          delay: values.length * 0.1,
        }}
        transform={`scale(${0.9 + 0.2 * averageVolume})`}
        style={{
          transformOrigin: "50% 50%",
          filter: "drop-shadow(0px 15px 28.1px rgba(125, 35, 5, 0.3))",
        }}
      />
    </svg>
  );
};
