"use client";

import { CloseIcon } from "@/components/CloseIcon";
import {
  AgentState,
  DisconnectButton,
  LiveKitRoom,
  RoomAudioRenderer,
  VoiceAssistantControlBar,
  useMultibandTrackVolume,
  useVoiceAssistant,
  useConnectionState,
  useRoomContext,
} from "@livekit/components-react";
import { useKrispNoiseFilter } from "@livekit/components-react/krisp";
import { AnimatePresence, motion } from "framer-motion";
import { MediaDeviceFailure, RoomEvent, ConnectionState } from "livekit-client";
import { useCallback, useEffect, useState, useRef } from "react";
import type { ConnectionDetails } from "./api/connection-details/route";
import Image from "next/image";

export default function Page() {
  const [connectionDetails, updateConnectionDetails] = useState<
    ConnectionDetails | undefined
  >(undefined);
  const [agentState, setAgentState] = useState<AgentState>("disconnected");
  const [connectionError, setConnectionError] = useState<string | null>(null);
  // Session counter to force LiveKitRoom remount
  const [sessionId, setSessionId] = useState(0);

  const onConnectButtonClicked = useCallback(async () => {
    // Prevent if already connecting or connected
    if (agentState === "connecting" || connectionDetails !== undefined) {
      console.log("Already connecting or connected, ignoring click");
      return;
    }

    try {
      setConnectionError(null);
      setAgentState("connecting");
      console.log("Initiating new connection...");

      const url = new URL(
        process.env.NEXT_PUBLIC_CONN_DETAILS_ENDPOINT ??
          "/api/connection-details",
        window.location.origin
      );
      console.log("Fetching connection details from:", url.toString());
      const response = await fetch(url.toString());
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to get connection details: ${response.status} ${errorText}`);
      }
      
      const connectionDetailsData = await response.json();
      console.log("Connection details received:", {
        serverUrl: connectionDetailsData.serverUrl,
        roomName: connectionDetailsData.roomName,
        participantName: connectionDetailsData.participantName,
      });
      updateConnectionDetails(connectionDetailsData);
    } catch (error) {
      console.error("Error getting connection details:", error);
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      setConnectionError(errorMessage);
      updateConnectionDetails(undefined);
      setAgentState("disconnected");
      alert(`Failed to connect: ${errorMessage}\n\nMake sure:\n1. The agent is running (python main.py dev)\n2. Environment variables are set correctly\n3. LiveKit server is accessible`);
    }
  }, [agentState, connectionDetails]);

  // Handle disconnection - reset everything and increment session
  const handleDisconnect = useCallback(() => {
    console.log("=== DISCONNECT HANDLER CALLED ===");
    console.log("Incrementing session ID to force remount");
    // Clear state first
    updateConnectionDetails(undefined);
    setAgentState("disconnected");
    setConnectionError(null);
    // Increment session to force LiveKitRoom remount
    setSessionId(prev => prev + 1);
  }, []);

  // Determine if we're in a connected/connecting session
  const isConnected = connectionDetails !== undefined;

  // Debug: log when connection state changes
  useEffect(() => {
    console.log("Page state - isConnected:", isConnected, "agentState:", agentState, "sessionId:", sessionId);
  }, [isConnected, agentState, sessionId]);

  return (
    <main data-lk-theme="default" className="h-full flex items-center">
      <div className="w-full grid grid-rows-[64px_1fr_8px] lg:border border-white/20 h-full min-h-dvh lg:max-w-5xl mx-auto lg:min-h-[640px] lg:max-h-[640px] rounded-2xl px-4">
        <header className="border-b border-white/20">
          <div className="py-4 px-2 flex items-center justify-between">
            <a href="https://groq.com" target="_blank">
              <Image
                width={122.667}
                height={64}
                src="/groq-logo.svg"
                alt="Groq logo"
                className="h-5 mt-2 w-auto"
              />
            </a>
            <div>
              Built with{" "}
              <a
                href="https://docs.livekit.io/agents"
                className="pb-[1px] border-b border-white/40 hover:border-white/80 transition-all duration-75 ease-out"
                target="_blank"
              >
                LiveKit
              </a>
            </div>
          </div>
        </header>
        
        {/* Content area - conditionally render LiveKitRoom or disconnected UI */}
        <div className="h-full flex flex-col gap-20 items-center justify-center bg-groq-accent-bg">
          {isConnected ? (
            <LiveKitRoom
              key={`session-${sessionId}-${connectionDetails.roomName}`}
              className="h-full w-full flex flex-col gap-20 items-center justify-center"
              token={connectionDetails.participantToken}
              serverUrl={connectionDetails.serverUrl}
              connect={true}
              audio={true}
              video={false}
              onMediaDeviceFailure={onDeviceFailure}
              onDisconnected={() => {
                console.log("LiveKitRoom onDisconnected callback fired");
                handleDisconnect();
              }}
              onError={(error) => {
                // Ignore "Client initiated disconnect" - this is expected when we disconnect
                const errorMsg = error.message || "Unknown error";
                if (errorMsg.includes("Client initiated disconnect")) {
                  console.log("Ignoring expected disconnect error");
                  return;
                }
                console.error("LiveKit connection error:", error);
                setConnectionError(`Connection error: ${errorMsg}`);
                handleDisconnect();
              }}
            >
              <ConnectedContent 
                onStateChange={setAgentState} 
                onDisconnect={handleDisconnect}
              />
            </LiveKitRoom>
          ) : (
            <DisconnectedContent
              agentState={agentState}
              connectionError={connectionError}
              onConnectButtonClicked={onConnectButtonClicked}
            />
          )}
        </div>
      </div>
    </main>
  );
}

// Content shown when connected to LiveKit room
function ConnectedContent(props: { 
  onStateChange: (state: AgentState) => void;
  onDisconnect: () => void;
}) {
  const { state, audioTrack } = useVoiceAssistant();
  const connectionState = useConnectionState();
  const room = useRoomContext();
  const krisp = useKrispNoiseFilter();
  const volumes = useMultibandTrackVolume(audioTrack ?? undefined, { bands: 1 });
  const volume = volumes?.[0] ?? 0;
  
  // Track if we've ever been connected - only trigger disconnect after being connected first
  const wasConnectedRef = useRef(false);
  // Track if we've already triggered disconnect to prevent multiple calls
  const disconnectTriggeredRef = useRef(false);

  // Enable krisp noise filter
  useEffect(() => {
    krisp.setNoiseFilterEnabled(true);
  }, []);

  // Track when we successfully connect
  useEffect(() => {
    if (connectionState === "connected") {
      console.log("Room is now CONNECTED - marking wasConnected = true");
      wasConnectedRef.current = true;
      disconnectTriggeredRef.current = false; // Reset disconnect flag on new connection
    }
  }, [connectionState]);

  // Report state changes to parent
  useEffect(() => {
    console.log("ConnectedContent - VoiceAssistant state:", state, "connectionState:", connectionState, "wasConnected:", wasConnectedRef.current);
    props.onStateChange(state);
  }, [props, state, connectionState]);

  // Listen to room events directly for more reliable disconnect detection
  useEffect(() => {
    if (!room) return;

    const handleDisconnected = () => {
      console.log("=== ROOM EVENT: Disconnected ===");
      if (!disconnectTriggeredRef.current) {
        disconnectTriggeredRef.current = true;
        props.onDisconnect();
      }
    };

    const handleConnectionStateChanged = (state: ConnectionState) => {
      console.log("=== ROOM EVENT: ConnectionStateChanged to", state, "===");
      if (state === ConnectionState.Disconnected && wasConnectedRef.current && !disconnectTriggeredRef.current) {
        console.log("Connection state changed to Disconnected - calling onDisconnect");
        disconnectTriggeredRef.current = true;
        props.onDisconnect();
      }
    };

    const handleParticipantDisconnected = (participant: any) => {
      console.log("=== ROOM EVENT: ParticipantDisconnected ===", participant?.identity);
      // Check if the agent (non-local participant) disconnected
      if (participant && !participant.isLocal) {
        console.log("Agent participant disconnected - triggering disconnect");
        if (!disconnectTriggeredRef.current) {
          disconnectTriggeredRef.current = true;
          // Small delay to allow farewell message to complete
          setTimeout(() => {
            props.onDisconnect();
          }, 500);
        }
      }
    };

    // Also check for room state changes periodically as a fallback
    const checkRoomState = () => {
      if (room.state === ConnectionState.Disconnected && wasConnectedRef.current && !disconnectTriggeredRef.current) {
        console.log("=== POLLING: Room state is Disconnected - calling onDisconnect ===");
        disconnectTriggeredRef.current = true;
        props.onDisconnect();
      }
    };
    
    // Poll room state every 2 seconds as fallback
    const pollInterval = setInterval(checkRoomState, 2000);

    room.on(RoomEvent.Disconnected, handleDisconnected);
    room.on(RoomEvent.ConnectionStateChanged, handleConnectionStateChanged);
    room.on(RoomEvent.ParticipantDisconnected, handleParticipantDisconnected);

    return () => {
      clearInterval(pollInterval);
      room.off(RoomEvent.Disconnected, handleDisconnected);
      room.off(RoomEvent.ConnectionStateChanged, handleConnectionStateChanged);
      room.off(RoomEvent.ParticipantDisconnected, handleParticipantDisconnected);
    };
  }, [room, props]);

  // Detect disconnection via hook - ONLY if we were previously connected and haven't triggered yet
  useEffect(() => {
    if (connectionState === "disconnected" && wasConnectedRef.current && !disconnectTriggeredRef.current) {
      console.log("=== HOOK: WAS CONNECTED, NOW DISCONNECTED - calling onDisconnect ===");
      disconnectTriggeredRef.current = true;
      props.onDisconnect();
    }
  }, [connectionState, props]);

  // Also detect when voice assistant state becomes "disconnected" (agent left)
  useEffect(() => {
    if (state === "disconnected" && wasConnectedRef.current && !disconnectTriggeredRef.current) {
      console.log("=== HOOK: VOICE ASSISTANT DISCONNECTED - calling onDisconnect ===");
      disconnectTriggeredRef.current = true;
      props.onDisconnect();
    }
  }, [state, props]);

  return (
    <>
      {/* Voice visualization orb */}
      <div className="flex flex-col items-center pt-12 justify-center">
        <motion.div
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        >
          <div
            className="w-48 h-48 rounded-full bg-white shadow-[inset_0px_-4px_20px_0px_rgba(0,0,0,0.5)]"
            style={{ transform: `scale(${1 + volume})` }}
          />
        </motion.div>
      </div>

      {/* Control bar with disconnect button */}
      <div className="relative h-12">
        <motion.div
          initial={{ opacity: 0, top: "10px" }}
          animate={{ opacity: 1, top: 0 }}
          transition={{ duration: 0.4, ease: [0.09, 1.04, 0.245, 1.055] }}
          className="flex h-8 absolute left-1/2 -translate-x-1/2 justify-center"
        >
          <VoiceAssistantControlBar controls={{ leave: false }} />
          <DisconnectButton>
            <CloseIcon />
          </DisconnectButton>
        </motion.div>
      </div>

      <RoomAudioRenderer />
    </>
  );
}

// Content shown when disconnected (no LiveKitRoom)
function DisconnectedContent(props: {
  agentState: AgentState;
  connectionError: string | null;
  onConnectButtonClicked: () => void;
}) {
  const [connectingDots, setConnectingDots] = useState("");

  // Animate dots while connecting
  useEffect(() => {
    if (props.agentState === "connecting") {
      const interval = setInterval(() => {
        setConnectingDots((prev) => (prev.length >= 3 ? "" : prev + "."));
      }, 250);
      return () => clearInterval(interval);
    } else {
      setConnectingDots("");
    }
  }, [props.agentState]);

  return (
    <>
      {/* Dimmed orb when disconnected */}
      <div className="flex flex-col items-center pt-12 justify-center opacity-10">
        <motion.div
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        >
          <div className="w-48 h-48 rounded-full bg-white shadow-[inset_0px_-4px_20px_0px_rgba(0,0,0,0.5)]" />
        </motion.div>
      </div>

      {/* Connect button */}
      <div className="relative h-12">
        {props.connectionError && (
          <div className="mb-2 text-red-400 text-xs text-center max-w-md mx-auto">
            {props.connectionError}
          </div>
        )}
        <motion.button
          initial={{ opacity: 0, top: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, ease: [0.09, 1.04, 0.245, 1.055] }}
          className={`min-w-56 uppercase px-2 py-1.5 rounded-lg border border-white/20 ${
            props.agentState === "connecting"
              ? "bg-white/5 cursor-not-allowed"
              : "bg-white/10 hover:bg-white/20 active:scale-[0.98]"
          } transition-all duration-75 ease-out`}
          onClick={() => props.agentState === "disconnected" && props.onConnectButtonClicked()}
          disabled={props.agentState === "connecting"}
        >
          <span className="text-white text-xs font-semibold tracking-widest">
            {props.agentState === "disconnected" ? (
              "Start a conversation"
            ) : (
              <>
                Connecting
                <span className="inline-block w-4 text-left">{connectingDots}</span>
              </>
            )}
          </span>
        </motion.button>
      </div>
    </>
  );
}

function onDeviceFailure(error?: MediaDeviceFailure) {
  console.error(error);
  alert(
    "Error acquiring camera or microphone permissions. Please make sure you grant the necessary permissions in your browser and reload the tab"
  );
}
