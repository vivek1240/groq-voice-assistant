import { RoomComponent } from "@/components/playground/RoomComponent";
import { AnimatePresence, motion } from "framer-motion";
import Head from "next/head";
import { useCallback, useState } from "react";

import { PlaygroundToast, ToastType } from "@/components/toast/PlaygroundToast";
import { ConfigProvider } from "@/hooks/useConfig";
import { ConnectionProvider } from "@/hooks/useConnection";

export default function Home() {
  return (
    <ConfigProvider>
      <ConnectionProvider>
        <HomeInner />
      </ConnectionProvider>
    </ConfigProvider>
  );
}

export function HomeInner() {
  const [toastMessage, setToastMessage] = useState<{
    message: string;
    type: ToastType;
  } | null>(null);

  return (
    <>
      <Head>
        <title>Cerebras Voice</title>
        <meta
          name="description"
          content="Talk to the world's fastest AI voice assistant, powered by Cerebras"
        />
        <meta name="og:title" content="Cerebras Voice" />
        <meta
          name="og:description"
          content="Talk to the world's fastest AI voice assistant, powered by Cerebras"
        />
        <meta
          property="og:image"
          content="https://cerebras.vercel.app/og.png"
        />
        <meta name="twitter:site" content="@LiveKit"></meta>
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="Cerebras Voice" />
        <meta
          name="twitter:description"
          content="Talk to the world's fastest AI voice assistant, powered by Cerebras"
        />
        <meta
          property="twitter:image"
          content="https://cerebras.vercel.app/og.png"
        />
        <meta property="twitter:image:width" content="1600" />
        <meta property="twitter:image:height" content="836" />
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"
        />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black" />
        <meta property="og:image:width" content="1600" />
        <meta property="og:image:height" content="836" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <main
        className={`relative flex overflow-x-hidden flex-col justify-center items-center h-full w-full bg-cerebras-content-bg repeating-square-background`}
      >
        <AnimatePresence>
          {toastMessage && (
            <motion.div
              className="left-0 right-0 top-0 absolute z-10"
              initial={{ opacity: 0, translateY: -50 }}
              animate={{ opacity: 1, translateY: 0 }}
              exit={{ opacity: 0, translateY: -50 }}
            >
              <PlaygroundToast
                message={toastMessage.message}
                type={toastMessage.type}
                onDismiss={() => {
                  setToastMessage(null);
                }}
              />
            </motion.div>
          )}
        </AnimatePresence>
        <RoomComponent />
      </main>
    </>
  );
}
