type PlaygroundHeader = {
  height: number;
};

export const PlaygroundHeader = ({ height }: PlaygroundHeader) => {
  return (
    <div
      className={`flex gap-4 pt-16 px-4 lg:px-8 text-cerebras-content-text w-full justify-center items-center shrink-0 bg-cerebras-content-bg`}
      style={{
        height: height + "px",
      }}
    >
      <div className="flex">
        <a href="https://console.groq.com/" target="_blank">
          <img
            width="108px"
            height="auto"
            src="/groq-logo.svg"
            alt="Groq logo"
          />
        </a>
      </div>
    </div>
  );
};
