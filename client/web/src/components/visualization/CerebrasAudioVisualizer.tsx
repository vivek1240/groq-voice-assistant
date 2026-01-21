import { useEffect, useState } from "react";
import { motion, useAnimation } from "framer-motion";

type VisualizerState =
  | "offline"
  | "listening"
  | "idle"
  | "speaking"
  | "thinking";

type CerebrasAudioVisualizerProps = {
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

const ringInactiveColor = "#E7E7E7";
const ringActiveColor = "#FFCFBF";

export const CerebrasAudioVisualizer = ({
  state,
  frequencies,
}: CerebrasAudioVisualizerProps) => {
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
    <>
      <CircleChart
        state={state}
        values={[90, 110, 120, 90]}
        frequencies={summedFrequencies.slice(0, 4)}
        radiusBase={isTabletOrSmaller ? 70 : 100}
      />
    </>
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
    frequencies.reduce((a, b) => a + b, 0) / frequencies.length;
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
          <stop offset="0%" stopColor="#F15A29" />
          <stop offset="20%" stopColor="#F15A29" />
          <stop offset="100%" stopColor="#FF835B" />
        </linearGradient>
      </defs>

      {values.map((value, index) => {
        const radius = radiusBase + index * (strokeWidth / 2 + gap);
        const circumference = 2 * Math.PI * radius;
        let halfCirc = circumference * 0.5;
        const volumeThreshold = index * 0.25;
        return (
          <motion.circle
            key={index}
            cx={size / 2}
            cy={size / 2}
            fill="none"
            strokeWidth={strokeWidth}
            initial={{
              strokeDasharray: `${halfCirc}, ${circumference}`,
              r: radiusBase + index * (strokeWidth / 2 + gap),
              stroke: ringInactiveColor,
            }}
            animate={
              isActive
                ? {
                    strokeDasharray: `${halfCirc * 2}, ${circumference}`,
                    r: radiusBase + index * (strokeWidth / 2 + gap),
                    stroke:
                      normalizedVolume > volumeThreshold
                        ? ringActiveColor
                        : ringInactiveColor,
                  }
                : {
                    r: radiusBase + index * (strokeWidth / 2 + gap),
                    strokeDasharray: `${halfCirc}, ${circumference}`,
                  }
            }
            transition={{
              duration: 1,
              type: "spring",
              stiffness: 90,
              damping: 20,
              delay: index * 0.1,
            }}
            transform={`rotate(${value} ${size / 2} ${size / 2})`}
          />
        );
      })}
      <motion.circle
        cx={size / 2}
        cy={size / 2}
        r={size * 0.1}
        fill="url(#orange-gradient)"
        animate={{
          r: isActive ? radiusBase * 0.75 : size * 0.18, // Animate between two sizes
          opacity: isActive ? 1 : 0.0,
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
