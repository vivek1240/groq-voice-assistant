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

export default function Page() {
  const [connectionDetails, updateConnectionDetails] = useState<
    ConnectionDetails | undefined
  >(undefined);
  const [agentState, setAgentState] = useState<AgentState>("disconnected");
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState(0);
  const [currentCallId, setCurrentCallId] = useState<string | null>(null);

  const onConnectButtonClicked = useCallback(async () => {
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
      setCurrentCallId(null); // Clear previous call ID when starting new call
    } catch (error) {
      console.error("Error getting connection details:", error);
      const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
      setConnectionError(errorMessage);
      updateConnectionDetails(undefined);
      setAgentState("disconnected");
      alert(`Failed to connect: ${errorMessage}\n\nMake sure:\n1. The agent is running (python main.py dev)\n2. Environment variables are set correctly\n3. LiveKit server is accessible`);
    }
  }, [agentState, connectionDetails]);

  const handleDisconnect = useCallback(() => {
    console.log("=== DISCONNECT HANDLER CALLED ===");
    // Don't clear currentCallId here - it should persist after disconnect
    // so we can show the call results
    updateConnectionDetails(undefined);
    setAgentState("disconnected");
    setConnectionError(null);
    setSessionId(prev => prev + 1);
  }, []);

  const isConnected = connectionDetails !== undefined;

  return (
    <main data-lk-theme="default" className="h-screen w-screen bg-gray-900 text-white overflow-hidden">
      <div className="h-full flex flex-col">
        {/* Header */}
        <header className="border-b border-white/20 px-6 py-4">
          <h1 className="text-2xl font-bold items-center">Pax Voice AI</h1>
        </header>

        {/* Main Content - Two Panel Layout */}
        <div className="flex-1 flex overflow-hidden">
          {/* LEFT PANEL - Call Interface */}
          <div className="flex-1 border-r border-white/20 flex flex-col overflow-hidden">
            <div className="px-6 py-4 border-b border-white/10">
              <h2 className="text-lg font-semibold uppercase tracking-wide">Call Interface</h2>
            </div>
            
            <div className="flex-1 flex flex-col items-center justify-center p-6 overflow-hidden">
              {isConnected ? (
                <LiveKitRoom
                  key={`session-${sessionId}-${connectionDetails.roomName}`}
                  className="h-full w-full flex flex-col"
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
                    roomName={connectionDetails.roomName}
                    onCallEnded={setCurrentCallId}
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

          {/* RIGHT PANEL - Evaluation Results */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="px-6 py-4 border-b border-white/10">
              <h2 className="text-lg font-semibold uppercase tracking-wide">Evaluation Results</h2>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6">
              <EvaluationResultsPanel callId={currentCallId} />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

// Content shown when connected to LiveKit room
function ConnectedContent(props: { 
  onStateChange: (state: AgentState) => void;
  onDisconnect: () => void;
  roomName: string;
  onCallEnded: (callId: string) => void;
}) {
  const { state, audioTrack } = useVoiceAssistant();
  const connectionState = useConnectionState();
  const room = useRoomContext();
  const krisp = useKrispNoiseFilter();
  const volumes = useMultibandTrackVolume(audioTrack ?? undefined, { bands: 1 });
  const volume = volumes?.[0] ?? 0;
  const onDisconnectRef = useRef(props.onDisconnect);
  const onStateChangeRef = useRef(props.onStateChange);
  const onCallEndedRef = useRef(props.onCallEnded);
  
  const wasConnectedRef = useRef(false);
  const disconnectTriggeredRef = useRef(false);
  const callIdSetRef = useRef(false);

  // Update refs when props change
  useEffect(() => {
    onDisconnectRef.current = props.onDisconnect;
    onStateChangeRef.current = props.onStateChange;
    onCallEndedRef.current = props.onCallEnded;
  }, [props.onDisconnect, props.onStateChange, props.onCallEnded]);

  useEffect(() => {
    krisp.setNoiseFilterEnabled(true);
  }, []);

  useEffect(() => {
    if (connectionState === ConnectionState.Connected) {
      console.log("Room is now CONNECTED - marking wasConnected = true");
      wasConnectedRef.current = true;
      disconnectTriggeredRef.current = false;
      callIdSetRef.current = false; // Reset when connecting
    }
  }, [connectionState]);

  useEffect(() => {
    onStateChangeRef.current(state);
  }, [state]);

  useEffect(() => {
    if (!room) return;

    const handleDisconnected = () => {
      console.log("=== ROOM EVENT: Disconnected ===");
      if (!disconnectTriggeredRef.current) {
        disconnectTriggeredRef.current = true;
        // Extract call ID from room name - format is call_<room_name>_<uuid>
        // We'll search for the file that starts with call_<room_name>_
        const callIdPrefix = `call_${props.roomName}_`;
        console.log("Room disconnected - setting call ID prefix:", callIdPrefix);
        onCallEndedRef.current(callIdPrefix);
        callIdSetRef.current = true;
        onDisconnectRef.current();
      }
    };

    const handleConnectionStateChanged = (state: ConnectionState) => {
      console.log("=== ROOM EVENT: ConnectionStateChanged to", state, "===");
      if (state === ConnectionState.Disconnected && wasConnectedRef.current && !disconnectTriggeredRef.current) {
        console.log("Connection state changed to Disconnected - calling onDisconnect");
        disconnectTriggeredRef.current = true;
        // Extract call ID from room name
        const callIdPrefix = `call_${props.roomName}_`;
        console.log("Connection disconnected - setting call ID prefix:", callIdPrefix);
        onCallEndedRef.current(callIdPrefix);
        onDisconnectRef.current();
      }
    };

    const handleParticipantDisconnected = (participant: any) => {
      console.log("=== ROOM EVENT: ParticipantDisconnected ===", participant?.identity);
      if (participant && !participant.isLocal) {
        console.log("Agent participant disconnected - triggering disconnect");
        if (!disconnectTriggeredRef.current) {
          disconnectTriggeredRef.current = true;
          // Extract call ID from room name
          const callIdPrefix = `call_${props.roomName}_`;
          console.log("Participant disconnected - setting call ID prefix:", callIdPrefix);
          onCallEndedRef.current(callIdPrefix);
          callIdSetRef.current = true;
          setTimeout(() => {
            onDisconnectRef.current();
          }, 500);
        }
      }
    };

    const checkRoomState = () => {
      if (room.state === ConnectionState.Disconnected && wasConnectedRef.current && !disconnectTriggeredRef.current) {
        console.log("=== POLLING: Room state is Disconnected - calling onDisconnect ===");
        disconnectTriggeredRef.current = true;
        // Extract call ID from room name
        const callIdPrefix = `call_${props.roomName}_`;
        console.log("Room state disconnected - setting call ID prefix:", callIdPrefix);
        onCallEndedRef.current(callIdPrefix);
        callIdSetRef.current = true;
        onDisconnectRef.current();
      }
    };
    
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
  }, [room]); // Removed props from dependencies to prevent infinite loop

  useEffect(() => {
    if (connectionState === ConnectionState.Disconnected && wasConnectedRef.current && !disconnectTriggeredRef.current) {
      console.log("=== HOOK: WAS CONNECTED, NOW DISCONNECTED - calling onDisconnect ===");
      disconnectTriggeredRef.current = true;
      // Extract call ID from room name
      const callIdPrefix = `call_${props.roomName}_`;
      console.log("Connection disconnected - setting call ID prefix:", callIdPrefix);
      onCallEndedRef.current(callIdPrefix);
      callIdSetRef.current = true;
      onDisconnectRef.current();
    }
  }, [connectionState, props.roomName]);

  useEffect(() => {
    if (state === "disconnected" && wasConnectedRef.current && !disconnectTriggeredRef.current) {
      console.log("=== HOOK: VOICE ASSISTANT DISCONNECTED - calling onDisconnect ===");
      disconnectTriggeredRef.current = true;
      // Set call ID when voice assistant disconnects
      const callIdPrefix = `call_${props.roomName}_`;
      console.log("Setting call ID prefix:", callIdPrefix);
      onCallEndedRef.current(callIdPrefix);
      callIdSetRef.current = true;
      onDisconnectRef.current();
    }
  }, [state, props.roomName]);

  return (
    <div className="w-full h-full flex flex-col gap-6">
      {/* Status Display */}
      <div className="text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 border border-white/20">
          <div className={`w-2 h-2 rounded-full ${
            connectionState === ConnectionState.Connected ? "bg-green-500" : 
            connectionState === ConnectionState.Connecting ? "bg-yellow-500" : 
            "bg-gray-500"
          }`} />
          <span className="text-sm font-medium">
            {connectionState === ConnectionState.Connected ? "Connected" : 
             connectionState === ConnectionState.Connecting ? "Connecting..." : 
             "Disconnected"}
          </span>
        </div>
      </div>

      {/* Voice visualization orb */}
      <div className="flex flex-col items-center justify-center flex-1">
        <motion.div
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        >
          <div
            className="w-48 h-48 rounded-full bg-white shadow-[inset_0px_-4px_20px_0px_rgba(0,0,0,0.5)]"
            style={{ transform: `scale(${1 + volume * 0.5})` }}
          />
        </motion.div>
      </div>


      {/* Call Controls */}
      <div className="flex items-center justify-center gap-4">
        <VoiceAssistantControlBar controls={{ leave: false }} />
        <DisconnectButton className="p-2 rounded-lg border border-white/20 hover:bg-white/10 transition-colors">
          <CloseIcon />
        </DisconnectButton>
      </div>

      <RoomAudioRenderer />
    </div>
  );
}

// Content shown when disconnected
function DisconnectedContent(props: {
  agentState: AgentState;
  connectionError: string | null;
  onConnectButtonClicked: () => void;
}) {
  const [connectingDots, setConnectingDots] = useState("");

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
    <div className="w-full flex flex-col items-center justify-center gap-6">
      {/* Dimmed orb when disconnected */}
      <div className="opacity-20">
        <motion.div
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        >
          <div className="w-48 h-48 rounded-full bg-white shadow-[inset_0px_-4px_20px_0px_rgba(0,0,0,0.5)]" />
        </motion.div>
      </div>

      {/* Status Display */}
      <div className="text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 border border-white/20">
          <div className="w-2 h-2 rounded-full bg-gray-500" />
          <span className="text-sm font-medium">Disconnected</span>
        </div>
      </div>

      {/* Start/End Call Button */}
      <div className="flex flex-col items-center gap-2">
        {props.connectionError && (
          <div className="mb-2 text-red-400 text-xs text-center max-w-md">
            {props.connectionError}
          </div>
        )}
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, ease: [0.09, 1.04, 0.245, 1.055] }}
          className={`min-w-56 uppercase px-6 py-3 rounded-lg border border-white/20 ${
            props.agentState === "connecting"
              ? "bg-white/5 cursor-not-allowed"
              : "bg-white/10 hover:bg-white/20 active:scale-[0.98]"
          } transition-all duration-75 ease-out`}
          onClick={() => props.agentState === "disconnected" && props.onConnectButtonClicked()}
          disabled={props.agentState === "connecting"}
        >
          <span className="text-white text-sm font-semibold tracking-widest">
            {props.agentState === "disconnected" ? (
              "Start Call"
            ) : (
              <>
                Connecting
                <span className="inline-block w-4 text-left">{connectingDots}</span>
              </>
            )}
          </span>
        </motion.button>
      </div>
    </div>
  );
}

// Evaluation Results Panel - Only shows current call data
function EvaluationResultsPanel({ callId }: { callId: string | null }) {
  const [callDetails, setCallDetails] = useState<any>(null);
  const [selectedTranscriptIndex, setSelectedTranscriptIndex] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCallDetails = async (callIdPrefix: string): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      console.log("Searching for call with prefix:", callIdPrefix);
      // Search for call by prefix (room name)
      const response = await fetch(`/api/calls/search?prefix=${encodeURIComponent(callIdPrefix)}`);
      console.log("Call search response status:", response.status);
      
      if (response.ok) {
        const data = await response.json();
        console.log("Call search response data:", data);
        if (data.call_id) {
          console.log("Found call ID, fetching full details:", data.call_id);
          // Now fetch full details
          const detailsResponse = await fetch(`/api/calls/${data.call_id}`);
          console.log("Call details response status:", detailsResponse.status);
          
          if (detailsResponse.ok) {
            const details = await detailsResponse.json();
            console.log("Call details fetched successfully:", {
              call_id: details.call_id,
              has_transcript: !!details.transcript,
              transcript_length: details.transcript?.length || 0,
              has_costs: !!details.costs,
            });
            setCallDetails(details);
            setError(null);
            setLoading(false);
            return true; // Success - stop retrying
          } else {
            const errorText = await detailsResponse.text();
            console.error("Error fetching call details:", detailsResponse.status, errorText);
            let errorMsg = `Failed to fetch call details (${detailsResponse.status})`;
            try {
              const errorData = JSON.parse(errorText);
              console.error("Error details:", errorData);
              if (errorData.error) errorMsg = errorData.error;
              if (errorData.details) {
                errorMsg += ` - Tried: ${errorData.details.evaluation_file || 'N/A'}`;
              }
            } catch {
              // Not JSON, that's okay
            }
            setError(errorMsg);
            setLoading(false);
            return false;
          }
        } else {
          console.log("No call_id in search response, will retry");
          setError("Call not found in search results");
          setLoading(false);
          return false;
        }
      } else {
        const errorText = await response.text();
        console.error("Error response from search:", response.status, errorText);
        let errorMsg = `Search failed (${response.status})`;
        try {
          const errorData = JSON.parse(errorText);
          console.error("Search error details:", errorData);
          if (errorData.error) errorMsg = errorData.error;
        } catch {
          // Not JSON, that's okay
        }
        setError(errorMsg);
        setLoading(false);
        return false;
      }
    } catch (error: any) {
      console.error("Error fetching call details:", error);
      setError(`Network error: ${error.message || 'Unknown error'}`);
      setLoading(false);
      return false;
    }
  };

  useEffect(() => {
    if (callId) {
      console.log("Call ID set, starting to fetch call details:", callId);
      setCallDetails(null); // Reset previous call details
      setSelectedTranscriptIndex(null);
      
      // Wait a bit for the metrics file to be written, then retry a few times
      let retries = 0;
      const maxRetries = 10; // Increased retries
      const retryInterval = 3000; // 3 seconds between retries
      let timeoutId: NodeJS.Timeout | null = null;
      
      const tryFetch = async () => {
        console.log(`Attempting to fetch call details (retry ${retries + 1}/${maxRetries})`);
        const success = await fetchCallDetails(callId);
        
        // If successful, stop retrying
        if (success) {
          console.log("Call details fetched successfully, stopping retries");
          return;
        }
        
        retries++;
        if (retries < maxRetries) {
          console.log(`Retry ${retries}/${maxRetries} failed, will retry in ${retryInterval}ms`);
          timeoutId = setTimeout(tryFetch, retryInterval);
        } else {
          console.log("Max retries reached, stopping fetch attempts");
        }
      };
      
      // Start first attempt after 3 seconds
      timeoutId = setTimeout(tryFetch, retryInterval);
      return () => {
        if (timeoutId) clearTimeout(timeoutId);
      };
    } else {
      console.log("Call ID cleared, resetting call details");
      setCallDetails(null);
      setSelectedTranscriptIndex(null);
      setError(null);
    }
  }, [callId]);

  return (
    <div className="space-y-6">
      {/* Debug: Show call ID status
      {callId && (
        <div className="text-xs text-white/50 mb-2 p-2 bg-white/5 rounded">
          Debug: Call ID = {callId} | Loading = {loading ? "true" : "false"} | Has Details = {callDetails ? "true" : "false"}
        </div>
      )} */}
      
      {/* Error Display */}
      {error && (
        <div className="text-xs text-red-400 mb-2 p-2 bg-red-500/10 border border-red-500/20 rounded">
          Error: {error}
        </div>
      )}
      
      {/* Cost Breakdown - Per Minute */}
      <section>
        <h3 className="text-base font-semibold mb-3 uppercase tracking-wide text-white/70">Cost Breakdown</h3>
        <div className="border border-white/20 rounded-lg p-4 bg-black/20 min-h-[150px]">
          {loading ? (
            <p className="text-sm text-white/50 italic">Loading cost data...</p>
          ) : callDetails?.costs ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-white/70">STT Cost/Min:</span>
                <span>${callDetails.costs.stt_per_minute?.toFixed(4) || "0.0000"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-white/70">LLM Cost/Min:</span>
                <span>${callDetails.costs.llm_per_minute?.toFixed(4) || "0.0000"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-white/70">TTS Cost/Min:</span>
                <span>${callDetails.costs.tts_per_minute?.toFixed(4) || "0.0000"}</span>
              </div>
              <div className="flex justify-between border-t border-white/10 pt-2 mt-2 font-semibold">
                <span>Total Cost/Min:</span>
                <span>${callDetails.cost_per_minute?.toFixed(4) || "0.0000"}</span>
              </div>
              <div className="flex justify-between text-xs text-white/50 mt-2 pt-2 border-t border-white/10">
                <span>Total Cost:</span>
                <span>${callDetails.costs.total?.toFixed(4) || "0.0000"}</span>
              </div>
            </div>
          ) : callId ? (
            <p className="text-sm text-white/50 italic">Waiting for call to end...</p>
          ) : (
            <p className="text-sm text-white/50 italic">No active call</p>
          )}
        </div>
      </section>

      {/* Transcript Dropdown */}
      <section>
        <h3 className="text-base font-semibold mb-3 uppercase tracking-wide text-white/70">Call Transcript</h3>
        <div className="border border-white/20 rounded-lg p-4 bg-black/20">
          {loading ? (
            <p className="text-sm text-white/50 italic">Loading transcript...</p>
          ) : callDetails?.transcript && callDetails.transcript.length > 0 ? (
            <>
              <select
                className="w-full mb-3 text-sm bg-white/10 border border-white/20 rounded px-3 py-2 text-black"
                value={selectedTranscriptIndex ?? ""}
                onChange={(e) => setSelectedTranscriptIndex(e.target.value ? parseInt(e.target.value) : null)}
              >
                <option value="">Select transcript entry...</option>
                {callDetails.transcript.map((entry: any, idx: number) => (
                  <option key={idx} value={idx}>
                    {entry.role === "user" ? "You" : "Agent"} - {entry.content.substring(0, 100)}...
                  </option>
                ))}
              </select>
              {selectedTranscriptIndex !== null && callDetails.transcript[selectedTranscriptIndex] && (
                <div className="mt-3 p-3 rounded bg-white/5 border border-white/10">
                  <div className="text-xs text-white/50 mb-1 uppercase tracking-wide">
                    {callDetails.transcript[selectedTranscriptIndex].role === "user" ? "You" : "Agent"}
                  </div>
                  <div className="text-sm text-white">
                    {callDetails.transcript[selectedTranscriptIndex].content}
                  </div>
                </div>
              )}
            </>
          ) : callId ? (
            <p className="text-sm text-white/50 italic">Transcript will appear after call ends</p>
          ) : (
            <p className="text-sm text-white/50 italic">No transcript available</p>
          )}
        </div>
      </section>
    </div>
  );
}

function onDeviceFailure(error?: MediaDeviceFailure) {
  console.error(error);
  alert(
    "Error acquiring camera or microphone permissions. Please make sure you grant the necessary permissions in your browser and reload the tab"
  );
}
