import { Button } from "@/components/button/Button";
import { ReactNode } from "react";

type PlaygroundHeader = {
  height: number;
};

export const PlaygroundHeader = ({ height }: PlaygroundHeader) => {
  return (
    <div
      className={`flex gap-4 py-10 border border-b-gray-200 px-4 lg:px-8 text-cerebras-content-text justify-between items-center shrink-0 bg-cerebras-content-bg`}
      style={{
        height: height + "px",
      }}
    >
      <div className="flex flex-col md:flex-row md:items-center md:gap-3 md:basis-2/3">
        <div className="flex md:basis-1/2">
          <a href="https://inference.cerebras.ai" target="_blank">
            <img
              width="108px"
              height="auto"
              src="/cerebras-logo.png"
              alt="Cerebras logo"
            />
          </a>
        </div>
        <div className="hidden md:block md:basis-1/2 md:text-center text-xs md:text-base text-cerebras-content-text font-bold">
          Voice Mode
        </div>
      </div>
      <div className="flex md:basis-1/3 justify-end items-center">
        <a href="https://github.com/livekit/agents" target="_blank">
          <div className="flex gap-[6px] items-center text-gray-700">
            <span className="font-semibold text-sm pt-[2px]">Built with</span>
            <div className="h-[14px]">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="auto"
                height="100%"
                viewBox="0 0 157 36"
                fill="none"
              >
                <path
                  d="M6.0417 0H0V35.4391H21.9177V30.2631H6.0417V0Z"
                  fill="currentColor"
                />
                <path
                  d="M31.8905 16.1333H26.0364V35.4373H31.8905V16.1333Z"
                  fill="currentColor"
                />
                <path
                  d="M49.1243 34.738L41.6781 10.3037H35.824L43.6453 35.4379H54.6034L62.4247 10.3037H56.5233L49.1243 34.738Z"
                  fill="currentColor"
                />
                <path
                  d="M76.9476 9.74658C69.3597 9.74658 64.5364 15.1563 64.5364 22.8497C64.5364 30.4974 69.2194 35.9998 76.9476 35.9998C82.8476 35.9998 87.1098 33.3883 88.7018 28.0256H82.749C81.8599 30.4504 80.2192 31.8986 76.9879 31.8986C73.4288 31.8986 70.9476 29.4268 70.4794 24.5787H89.1186C89.2076 23.9606 89.2541 23.3372 89.2575 22.7128C89.2589 14.8755 84.3883 9.74658 76.9476 9.74658ZM70.5253 20.5176C71.1352 15.9959 73.5232 13.8506 76.9476 13.8506C80.5527 13.8506 82.988 16.5077 83.27 20.5176H70.5253Z"
                  fill="currentColor"
                />
                <path
                  d="M123.491 0H115.904L101.199 16.2278V0H95.1575V35.4391H101.199V17.5335L117.403 35.4391H125.13L108.177 16.7866L123.491 0Z"
                  fill="currentColor"
                />
                <path
                  d="M133.604 10.3037H127.75V29.6077H133.604V10.3037Z"
                  fill="currentColor"
                />
                <path
                  d="M26.037 10.3037H20.1829V16.1325H26.037V10.3037Z"
                  fill="currentColor"
                />
                <path
                  d="M139.459 29.6099H133.605V35.4387H139.459V29.6099Z"
                  fill="currentColor"
                />
                <path
                  d="M156.951 29.6099H151.097V35.4387H156.951V29.6099Z"
                  fill="currentColor"
                />
                <path
                  d="M156.951 16.1337V10.3049H151.097V0H145.242V10.3049H139.388V16.1337H145.242V29.6103H151.097V16.1337H156.951Z"
                  fill="currentColor"
                />
              </svg>
            </div>
          </div>
        </a>
      </div>
    </div>
  );
};
