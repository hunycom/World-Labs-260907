/**
 * World Labs Spark 3D - AI Voice Assistant (Nova)
 * Supports OpenAI Pipeline (Whisper STT -> GPT-4o-mini Tool Calling -> Nova TTS)
 * with graceful Browser Native fallback (Web Speech API + speechSynthesis).
 */

(function () {
  "use strict";

  // State Management
  const state = {
    apiKey: localStorage.getItem("OPENAI_API_KEY") || "",
    isListening: false,
    isProcessing: false,
    isSpeaking: false,
    mediaRecorder: null,
    audioChunks: [],
    speechRecognition: null,
    audioElement: null,
    silenceTimer: null,
    audioContext: null,
    analyser: null,
  };

  // Section Mapping
  const sectionMap = {
    spatialLab: "#spatialLabSection",
    awards: "#awardScroll",
    faq: "#faqScroll",
    about: "#aboutScroll",
    services: "#serviceScroll",
    whitepapers: "#whitepaperSection",
    contact: "#contactScroll",
    works: "#workScroll",
  };

  // Action Dispatcher
  function executeAction(actionName, params = {}) {
    console.log(`[Nova Voice Action] Executing: ${actionName}`, params);
    let desc = "";

    switch (actionName) {
      case "trigger_physics": {
        const mode = params.action || "drop";
        const labSec = document.querySelector("#spatialLabSection");
        if (labSec) labSec.scrollIntoView({ behavior: "smooth" });

        setTimeout(() => {
          if (mode === "drop") {
            const btn = document.getElementById("btnDropTest");
            if (btn) btn.click();
            desc = "1m 상자 낙하 시뮬레이션 실행";
          } else if (mode === "toss") {
            const btn = document.getElementById("btnTossTest");
            if (btn) btn.click();
            desc = "2.5m/s 상자 투척 시뮬레이션 실행";
          } else if (mode === "reset") {
            const btn = document.getElementById("btnResetPhysics");
            if (btn) btn.click();
            desc = "물리 시뮬레이션 및 카메라 초기화";
          }
        }, 300);
        break;
      }

      case "toggle_wireframe": {
        const btn = document.getElementById("btnToggleWire");
        if (btn) btn.click();
        desc = "와이어프레임 렌더링 토글";
        break;
      }

      case "toggle_partition": {
        const btn = document.getElementById("btnTogglePartition");
        if (btn) btn.click();
        desc = "7부품 공간 분할(OBB) 토글";
        break;
      }

      case "run_picking_benchmark": {
        const labSec = document.querySelector("#spatialLabSection");
        if (labSec) labSec.scrollIntoView({ behavior: "smooth" });
        setTimeout(() => {
          const btn = document.getElementById("btnRunPicking");
          if (btn) btn.click();
        }, 300);
        desc = "60점 레이캐스팅 정확도 평가 가동";
        break;
      }

      case "navigate_section": {
        const secId = sectionMap[params.section] || params.section;
        if (secId) {
          const target = document.querySelector(secId);
          if (target) {
            target.scrollIntoView({ behavior: "smooth" });
            desc = `${secId} 섹션으로 이동`;
          }
        }
        break;
      }

      case "open_car_physics": {
        desc = "자동차 3D 물리 엔진 페이지로 이동";
        setTimeout(() => {
          window.location.href = "car-physics.html";
        }, 1200);
        break;
      }

      case "toggle_fullscreen": {
        const btn = document.getElementById("btnFullscreen");
        if (btn) btn.click();
        desc = "3D 뷰포트 전체화면 모드 전환";
        break;
      }

      case "generate_3d_world": {
        const prompt = params.prompt || "";
        const input = document.getElementById("inputWorldPrompt");
        const btn = document.getElementById("btnGenerateWorld");
        const labSec = document.querySelector("#spatialLabSection");
        if (labSec) labSec.scrollIntoView({ behavior: "smooth" });
        if (input && prompt) {
          input.value = prompt;
          if (btn) {
            setTimeout(() => btn.click(), 400);
          }
          desc = `AI 3D 월드 생성: "${prompt}"`;
        }
        break;
      }

      default:
        console.warn("[Nova] Unknown action:", actionName);
    }

    if (desc) {
      updateActionBadge(desc);
    }
    return desc;
  }

  // Local Intent Rule Parser (Fallback for free mode or quick matching)
  function parseLocalIntent(text) {
    const t = text.toLowerCase().replace(/\s+/g, "");

    if (t.includes("낙하") || t.includes("떨어") || t.includes("1미터") || t.includes("1m") || t.includes("상자낙하")) {
      executeAction("trigger_physics", { action: "drop" });
      return "네, 1미터 상자 낙하 시뮬레이션을 실행했습니다.";
    }
    if (t.includes("던져") || t.includes("투척") || t.includes("날려") || t.includes("2.5m")) {
      executeAction("trigger_physics", { action: "toss" });
      return "통로 방향으로 2.5m/s 상자 투척 시뮬레이션을 실행합니다.";
    }
    if (t.includes("리셋") || t.includes("초기화") || t.includes("원래대로") || t.includes("처음")) {
      executeAction("trigger_physics", { action: "reset" });
      return "물리 시뮬레이션과 카메라 위치를 초기 상태로 리셋했습니다.";
    }
    if (t.includes("와이어") || t.includes("격자") || t.includes("그리드") || t.includes("와이어프레임")) {
      executeAction("toggle_wireframe");
      return "와이어프레임 렌더링 표시 상태를 전환했습니다.";
    }
    if (t.includes("분할") || t.includes("바운딩") || t.includes("obb") || t.includes("7부품") || t.includes("박스표시")) {
      executeAction("toggle_partition");
      return "7부품 공간 분할 OBB 경계를 표시합니다.";
    }
    if (t.includes("피킹") || t.includes("레이캐스팅") || t.includes("정확도") || t.includes("오딧") || t.includes("검사")) {
      executeAction("run_picking_benchmark");
      return "60점 레이캐스팅 정확도 평가 벤치마크를 시작합니다.";
    }
    if (t.includes("창고") || t.includes("시뮬레이터") || t.includes("연구실") || t.includes("랩") || t.includes("스마트창고")) {
      executeAction("navigate_section", { section: "spatialLab" });
      return "3D 스마트 물류창고 연구실 섹션으로 이동합니다.";
    }
    if (t.includes("자동차") || t.includes("차량") || t.includes("카피직스") || t.includes("차")) {
      executeAction("open_car_physics");
      return "자동차 3D 물리 시뮬레이터 페이지로 이동합니다.";
    }
    if (t.includes("질문") || t.includes("faq") || t.includes("자주묻는")) {
      executeAction("navigate_section", { section: "faq" });
      return "자주 묻는 질문(FAQ) 섹션으로 이동합니다.";
    }
    if (t.includes("벤치마크") || t.includes("인증") || t.includes("상") || t.includes("성과")) {
      executeAction("navigate_section", { section: "awards" });
      return "공식 벤치마크 및 글로벌 표준 인증 섹션으로 이동합니다.";
    }
    if (t.includes("소개") || t.includes("월드랩스") || t.includes("회사") || t.includes("about")) {
      executeAction("navigate_section", { section: "about" });
      return "월드랩스 공간 지능 소개 섹션으로 이동합니다.";
    }
    if (t.includes("전체화면") || t.includes("크게") || t.includes("화면확대")) {
      executeAction("toggle_fullscreen");
      return "3D 뷰포트 전체화면 모드를 전환합니다.";
    }

    return "말씀하신 명령을 접수했습니다. 스마트 창고 시뮬레이터 또는 특정 섹션으로 안내해 드릴게요.";
  }

  // OpenAI Tool Definitions for GPT-4o-mini
  const openAITools = [
    {
      type: "function",
      function: {
        name: "trigger_physics",
        description: "3D 공간 물리 시뮬레이션 충돌 액션을 실행합니다.",
        parameters: {
          type: "object",
          properties: {
            action: {
              type: "string",
              enum: ["drop", "toss", "reset"],
              description: "drop: 1m 상자 낙하, toss: 2.5m/s 투척 충돌, reset: 초기화"
            }
          },
          required: ["action"]
        }
      }
    },
    {
      type: "function",
      function: {
        name: "navigate_section",
        description: "웹페이지 내 특정 섹션으로 부드럽게 스크롤 이동합니다.",
        parameters: {
          type: "object",
          properties: {
            section: {
              type: "string",
              enum: ["spatialLab", "awards", "faq", "about", "services", "whitepapers", "contact", "works"],
              description: "이동할 대상 섹션 ID"
            }
          },
          required: ["section"]
        }
      }
    },
    {
      type: "function",
      function: {
        name: "toggle_wireframe",
        description: "3D 스마트 물류창고 바닥 및 랙 와이어프레임 렌더링 표시를 켜거나 끕니다.",
        parameters: { type: "object", properties: {} }
      }
    },
    {
      type: "function",
      function: {
        name: "toggle_partition",
        description: "7부품 공간 분할 OBB(지향성 바운딩 박스) 표시를 켜거나 끕니다.",
        parameters: { type: "object", properties: {} }
      }
    },
    {
      type: "function",
      function: {
        name: "run_picking_benchmark",
        description: "60점 레이캐스팅 정확도 평가 벤치마크 루틴을 가동합니다.",
        parameters: { type: "object", properties: {} }
      }
    },
    {
      type: "function",
      function: {
        name: "open_car_physics",
        description: "자동차 3D 물리 시뮬레이터 페이지(car-physics.html)로 이동합니다.",
        parameters: { type: "object", properties: {} }
      }
    },
    {
      type: "function",
      function: {
        name: "toggle_fullscreen",
        description: "3D 뷰포트 전체화면 모드를 전환합니다.",
        parameters: { type: "object", properties: {} }
      }
    },
    {
      type: "function",
      function: {
        name: "generate_3d_world",
        description: "AI 텍스트 프롬프트를 기입하고 새로운 3D 공간을 실시간 생성합니다.",
        parameters: {
          type: "object",
          properties: {
            prompt: { type: "string", description: "생성할 3D 공간 설명 (영문/한글)" }
          },
          required: ["prompt"]
        }
      }
    }
  ];

  // OpenAI API Calls
  async function callWhisperSTT(audioBlob) {
    const formData = new FormData();
    formData.append("file", audioBlob, "speech.webm");
    formData.append("model", "whisper-1");
    formData.append("language", "ko");
    formData.append("prompt", "World Labs, Spark 3D, 3DGS, 가우시안 스플래팅, 래피어, Rapier, 물리 엔진, OBB, 레이캐스팅, 피킹, 스마트 창고, 디지털 트윈");

    const resp = await fetch("https://api.openai.com/v1/audio/transcriptions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${state.apiKey}`
      },
      body: formData
    });

    if (!resp.ok) {
      const err = await resp.text();
      throw new Error(`Whisper STT 실패 (${resp.status}): ${err}`);
    }

    const data = await resp.json();
    return data.text || "";
  }

  async function callGPT4oMini(userText) {
    const messages = [
      {
        role: "system",
        content: "당신은 World Labs Spark 3D 공간 지능 포털의 공식 AI 음성 어시스턴트 'Nova'입니다. 사용자의 음성 요청을 분석하여 적절한 화면 제어 도구(tools)를 호출하고, 친절하고 세련되며 지적인 한국어 여성 비서 톤으로 1~2문장의 간결한 답변을 반환하세요. 화면 조작이 필요 없는 일반 질문인 경우에도 지적이고 정중하게 답변하세요."
      },
      {
        role: "user",
        content: userText
      }
    ];

    const resp = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${state.apiKey}`
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        messages: messages,
        tools: openAITools,
        tool_choice: "auto",
        temperature: 0.7
      })
    });

    if (!resp.ok) {
      const err = await resp.text();
      throw new Error(`GPT-4o-mini 호출 실패 (${resp.status}): ${err}`);
    }

    const data = await resp.json();
    const choice = data.choices[0];
    const message = choice.message;

    // Check if tools were called
    if (message.tool_calls && message.tool_calls.length > 0) {
      for (const tc of message.tool_calls) {
        const fnName = tc.function.name;
        let fnArgs = {};
        try {
          fnArgs = JSON.parse(tc.function.arguments);
        } catch (e) {
          console.warn("[Nova] Failed to parse tool arguments:", e);
        }
        executeAction(fnName, fnArgs);
      }
    }

    return message.content || "네, 요청하신 작업을 브라우저에서 실행했습니다.";
  }

  async function callOpenAITTS(text) {
    const resp = await fetch("https://api.openai.com/v1/audio/speech", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${state.apiKey}`
      },
      body: JSON.stringify({
        model: "tts-1",
        voice: "nova",
        input: text,
        speed: 1.05
      })
    });

    if (!resp.ok) {
      const err = await resp.text();
      throw new Error(`OpenAI TTS 실패 (${resp.status}): ${err}`);
    }

    const audioBlob = await resp.blob();
    return URL.createObjectURL(audioBlob);
  }

  // Speech Output Helper
  function speakResponse(text, audioUrl = null) {
    state.isSpeaking = true;
    updateStatus("speaking", "Nova 답변 중...");

    if (audioUrl) {
      if (state.audioElement) {
        state.audioElement.pause();
      }
      state.audioElement = new Audio(audioUrl);
      state.audioElement.onended = () => {
        state.isSpeaking = false;
        updateStatus("idle", "대기 중");
      };
      state.audioElement.onerror = () => {
        state.isSpeaking = false;
        updateStatus("idle", "대기 중");
      };
      state.audioElement.play().catch((e) => {
        console.warn("[Nova] Audio play error:", e);
        state.isSpeaking = false;
        updateStatus("idle", "대기 중");
      });
    } else if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.lang = "ko-KR";
      utter.rate = 1.0;

      // Try selecting female Korean voice if available
      const voices = window.speechSynthesis.getVoices();
      const koFemale = voices.find(
        (v) => v.lang.includes("ko") && (v.name.includes("Female") || v.name.includes("Yuna") || v.name.includes("Sun-Hi") || v.name.includes("Google 한국어"))
      ) || voices.find((v) => v.lang.includes("ko"));
      if (koFemale) utter.voice = koFemale;

      utter.onend = () => {
        state.isSpeaking = false;
        updateStatus("idle", "대기 중");
      };
      utter.onerror = () => {
        state.isSpeaking = false;
        updateStatus("idle", "대기 중");
      };
      window.speechSynthesis.speak(utter);
    } else {
      state.isSpeaking = false;
      updateStatus("idle", "대기 중");
    }
  }

  // Processing pipeline
  async function handleAudioProcessing(audioBlob) {
    state.isProcessing = true;
    updateStatus("processing", "AI 분석 및 화면 제어 중...");

    try {
      if (state.apiKey) {
        // OpenAI Pipeline: Whisper -> GPT-4o-mini -> Nova TTS
        updateTranscript("음성을 텍스트로 변환하는 중...");
        const userText = await callWhisperSTT(audioBlob);
        updateTranscript(userText);

        updateResponse("Nova가 화면 제어 명령을 생성하는 중...");
        const replyText = await callGPT4oMini(userText);
        updateResponse(replyText);

        try {
          const audioUrl = await callOpenAITTS(replyText);
          speakResponse(replyText, audioUrl);
        } catch (ttsErr) {
          console.warn("[Nova] TTS failed, falling back to browser speech:", ttsErr);
          speakResponse(replyText, null);
        }
      } else {
        console.log("[Nova] In browser free mode");
      }
    } catch (err) {
      console.error("[Nova] Processing error:", err);
      updateResponse(`오류가 발생했습니다: ${err.message}`);
      updateStatus("idle", "오류 발생 (다시 시도해 주세요)");
    } finally {
      state.isProcessing = false;
    }
  }

  // Voice Recognition Controls
  async function startListening() {
    if (state.isListening || state.isProcessing) return;

    if (state.apiKey) {
      // Use MediaRecorder for Whisper STT
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        state.audioChunks = [];
        state.mediaRecorder = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "" });

        state.mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) state.audioChunks.push(e.data);
        };

        state.mediaRecorder.onstop = () => {
          const audioBlob = new Blob(state.audioChunks, { type: "audio/webm" });
          stream.getTracks().forEach((track) => track.stop());
          if (state.audioChunks.length > 0) {
            handleAudioProcessing(audioBlob);
          }
        };

        state.mediaRecorder.start();
        state.isListening = true;
        updateStatus("listening", "말씀하세요... (음성 듣는 중)");
        updateTranscript("🎙️ 음성을 듣고 있습니다...");
        startWaveAnimation();
      } catch (err) {
        console.error("[Nova] Mic access denied:", err);
        alert("마이크 사용 권한이 필요합니다. 브라우저 설정에서 마이크 접근을 허용해 주세요.");
      }
    } else {
      // Free Browser SpeechRecognition Fallback
      const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRec) {
        alert("이 브라우저는 음성 인식을 지원하지 않습니다. Chrome 또는 Edge 브라우저를 이용하시거나 OpenAI API Key를 등록해 주세요.");
        return;
      }

      state.speechRecognition = new SpeechRec();
      state.speechRecognition.lang = "ko-KR";
      state.speechRecognition.continuous = false;
      state.speechRecognition.interimResults = false;

      state.speechRecognition.onstart = () => {
        state.isListening = true;
        updateStatus("listening", "말씀하세요... (무료 모드)");
        updateTranscript("🎙️ 말씀하세요... (예: '1m 상자 떨어뜨려 줘')");
        startWaveAnimation();
      };

      state.speechRecognition.onresult = (e) => {
        const text = e.results[0][0].transcript;
        updateTranscript(text);
        stopWaveAnimation();
        updateStatus("processing", "명령 분석 및 화면 제어 중...");

        const reply = parseLocalIntent(text);
        updateResponse(reply);
        speakResponse(reply, null);
      };

      state.speechRecognition.onerror = (e) => {
        console.warn("[Nova] SpeechRecognition error:", e);
        stopWaveAnimation();
        state.isListening = false;
        updateStatus("idle", "대기 중");
      };

      state.speechRecognition.onend = () => {
        stopWaveAnimation();
        state.isListening = false;
        if (!state.isSpeaking && !state.isProcessing) {
          updateStatus("idle", "대기 중");
        }
      };

      try {
        state.speechRecognition.start();
      } catch (e) {
        console.warn("[Nova] SpeechRec start err:", e);
      }
    }
  }

  function stopListening() {
    if (!state.isListening) return;
    state.isListening = false;
    stopWaveAnimation();

    if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
      state.mediaRecorder.stop();
    }
    if (state.speechRecognition) {
      try {
        state.speechRecognition.stop();
      } catch (e) {}
    }
  }

  // UI Construction & DOM Elements
  function createVoiceAssistantUI() {
    // Inject Styles
    const style = document.createElement("style");
    style.id = "nova-voice-styles";
    style.textContent = `
      #voiceAssistantFab {
        position: fixed;
        bottom: 88px;
        right: 20px;
        width: 52px;
        height: 52px;
        border-radius: 50%;
        background: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%);
        box-shadow: 0 4px 20px rgba(56, 189, 248, 0.45);
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        z-index: 1040;
        border: 1px solid rgba(255, 255, 255, 0.3);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
      }
      #voiceAssistantFab:hover {
        transform: scale(1.08);
        box-shadow: 0 6px 28px rgba(56, 189, 248, 0.65);
      }
      #voiceAssistantFab .pulse-ring {
        position: absolute;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        border: 2px solid #38bdf8;
        animation: novaPulse 2s infinite cubic-bezier(0.4, 0, 0.2, 1);
        pointer-events: none;
      }
      @keyframes novaPulse {
        0% { transform: scale(1); opacity: 0.8; }
        100% { transform: scale(1.6); opacity: 0; }
      }
      #voiceAssistantModal {
        position: fixed;
        bottom: 150px;
        right: 20px;
        width: 380px;
        max-width: calc(100vw - 32px);
        background: rgba(10, 15, 26, 0.92);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(56, 189, 248, 0.35);
        border-radius: 20px;
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.8), 0 0 35px rgba(56, 189, 248, 0.15);
        z-index: 1050;
        display: none;
        flex-direction: column;
        overflow: hidden;
        animation: novaSlideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      }
      @keyframes novaSlideUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
      }
      .nova-head {
        padding: 14px 18px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(255, 255, 255, 0.03);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      }
      .nova-title-wrap {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .nova-status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #38bdf8;
        box-shadow: 0 0 8px #38bdf8;
      }
      .nova-status-dot.listening {
        background: #22c55e;
        box-shadow: 0 0 10px #22c55e;
        animation: blinkDot 0.8s infinite alternate;
      }
      .nova-status-dot.processing {
        background: #a855f7;
        box-shadow: 0 0 10px #a855f7;
      }
      .nova-status-dot.speaking {
        background: #f59e0b;
        box-shadow: 0 0 10px #f59e0b;
      }
      @keyframes blinkDot {
        from { opacity: 0.3; }
        to { opacity: 1; }
      }
      .nova-title {
        font-size: 13px;
        font-weight: 800;
        letter-spacing: 1px;
        color: #ffffff;
      }
      .nova-badge-mode {
        font-size: 10px;
        padding: 2px 7px;
        border-radius: 12px;
        background: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
        font-weight: 700;
      }
      .nova-actions {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .nova-btn-icon {
        background: transparent;
        border: none;
        color: rgba(255, 255, 255, 0.6);
        cursor: pointer;
        padding: 4px;
        font-size: 14px;
        border-radius: 6px;
        transition: color 0.2s, background 0.2s;
      }
      .nova-btn-icon:hover {
        color: #ffffff;
        background: rgba(255, 255, 255, 0.1);
      }
      .nova-body {
        padding: 16px 18px;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .nova-status-text {
        font-size: 11px;
        color: #94a3b8;
        font-weight: 600;
        letter-spacing: 0.5px;
      }
      .nova-visualizer {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 4px;
        height: 28px;
      }
      .nova-wave-bar {
        width: 3px;
        height: 6px;
        background: #38bdf8;
        border-radius: 3px;
        transition: height 0.15s ease;
      }
      .nova-visualizer.active .nova-wave-bar:nth-child(1) { animation: wave 0.8s infinite 0.1s; }
      .nova-visualizer.active .nova-wave-bar:nth-child(2) { animation: wave 0.8s infinite 0.25s; }
      .nova-visualizer.active .nova-wave-bar:nth-child(3) { animation: wave 0.8s infinite 0.4s; }
      .nova-visualizer.active .nova-wave-bar:nth-child(4) { animation: wave 0.8s infinite 0.25s; }
      .nova-visualizer.active .nova-wave-bar:nth-child(5) { animation: wave 0.8s infinite 0.1s; }
      @keyframes wave {
        0%, 100% { height: 6px; }
        50% { height: 26px; }
      }
      .nova-chat-box {
        display: flex;
        flex-direction: column;
        gap: 8px;
        max-height: 160px;
        overflow-y: auto;
      }
      .nova-bubble-user {
        font-size: 12px;
        line-height: 1.4;
        color: #cbd5e1;
        background: rgba(255, 255, 255, 0.05);
        padding: 8px 12px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
      }
      .nova-bubble-ai {
        font-size: 12px;
        line-height: 1.45;
        color: #ffffff;
        background: rgba(56, 189, 248, 0.12);
        padding: 8px 12px;
        border-radius: 12px;
        border: 1px solid rgba(56, 189, 248, 0.3);
      }
      .nova-action-badge {
        font-size: 11px;
        font-weight: 700;
        color: #38bdf8;
        background: rgba(56, 189, 248, 0.15);
        border: 1px dashed #38bdf8;
        padding: 6px 10px;
        border-radius: 8px;
        display: none;
        align-items: center;
        gap: 6px;
      }
      .nova-btn-talk {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        width: 100%;
        padding: 11px 16px;
        border-radius: 12px;
        background: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%);
        color: #ffffff;
        font-size: 13px;
        font-weight: 700;
        border: none;
        cursor: pointer;
        box-shadow: 0 4px 16px rgba(56, 189, 248, 0.35);
        transition: transform 0.2s, box-shadow 0.2s;
      }
      .nova-btn-talk:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 22px rgba(56, 189, 248, 0.55);
      }
      .nova-btn-talk.recording {
        background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
        box-shadow: 0 4px 16px rgba(239, 68, 68, 0.45);
        animation: pulseRed 1.2s infinite alternate;
      }
      @keyframes pulseRed {
        from { transform: scale(1); }
        to { transform: scale(1.02); }
      }
      .nova-quick-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        padding-top: 4px;
      }
      .nova-chip {
        font-size: 10px;
        color: #94a3b8;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 4px 8px;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s;
      }
      .nova-chip:hover {
        color: #ffffff;
        background: rgba(56, 189, 248, 0.2);
        border-color: #38bdf8;
      }
      .nova-settings-drawer {
        display: none;
        flex-direction: column;
        gap: 8px;
        padding: 12px;
        background: rgba(0, 0, 0, 0.3);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
      }
      .nova-settings-drawer input {
        width: 100%;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 11px;
        color: #ffffff;
        outline: none;
      }
      .nova-settings-drawer input:focus {
        border-color: #38bdf8;
      }
      .nova-settings-btn-row {
        display: flex;
        gap: 6px;
      }
      .nova-btn-sub {
        flex: 1;
        padding: 5px 8px;
        font-size: 11px;
        font-weight: 600;
        border-radius: 6px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
        cursor: pointer;
      }
      .nova-btn-sub:hover {
        background: rgba(255, 255, 255, 0.15);
      }
      .nova-btn-sub.primary {
        background: #0284c7;
        border-color: #38bdf8;
      }
    `;
    document.head.appendChild(style);

    // Floating FAB Button
    const fab = document.createElement("div");
    fab.id = "voiceAssistantFab";
    fab.title = "AI 음성 제어 어시스턴트 (Nova)";
    fab.innerHTML = `
      <div class="pulse-ring"></div>
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
        <line x1="12" y1="19" x2="12" y2="22"></line>
      </svg>
    `;
    document.body.appendChild(fab);

    // Modal HUD
    const modal = document.createElement("div");
    modal.id = "voiceAssistantModal";
    modal.innerHTML = `
      <div class="nova-head">
        <div class="nova-title-wrap">
          <div class="nova-status-dot" id="novaStatusDot"></div>
          <span class="nova-title">NOVA SPATIAL AI</span>
          <span class="nova-badge-mode" id="novaModeBadge">${state.apiKey ? "OpenAI Nova" : "브라우저 무료 모드"}</span>
        </div>
        <div class="nova-actions">
          <button class="nova-btn-icon" id="novaBtnSettings" title="OpenAI API Key 설정">⚙️</button>
          <button class="nova-btn-icon" id="novaBtnClose" title="닫기">✕</button>
        </div>
      </div>
      <div class="nova-body">
        <div class="d-flex justify-content-between align-items-center">
          <span class="nova-status-text" id="novaStatusText">대기 중</span>
          <div class="nova-visualizer" id="novaVisualizer">
            <span class="nova-wave-bar"></span>
            <span class="nova-wave-bar"></span>
            <span class="nova-wave-bar"></span>
            <span class="nova-wave-bar"></span>
            <span class="nova-wave-bar"></span>
          </div>
        </div>

        <div class="nova-settings-drawer" id="novaSettingsDrawer">
          <span style="font-size: 11px; color: #cbd5e1; font-weight: 700;">OpenAI API Key 설정 (선택 사항)</span>
          <input type="password" id="novaApiKeyInput" placeholder="sk-..." value="${state.apiKey}">
          <p style="font-size: 10px; color: #94a3b8; margin: 0; line-height: 1.4;">
            키를 저장하시면 Whisper 고정밀 STT와 한국어 여성 음성(nova)이 가동됩니다. 미입력 시 브라우저 내장 무료 모드로 즉시 작동합니다.
          </p>
          <div class="nova-settings-btn-row">
            <button class="nova-btn-sub primary" id="novaBtnSaveKey">키 저장</button>
            <button class="nova-btn-sub" id="novaBtnRemoveKey">삭제 (무료 전환)</button>
          </div>
        </div>

        <div class="nova-chat-box">
          <div class="nova-bubble-user" id="novaUserBubble">
            🗣️ "상자 떨어뜨려 줘", "와이어프레임 켜줘" 등 음성으로 명령해 보세요.
          </div>
          <div class="nova-bubble-ai" id="novaAiBubble">
            ✨ 안녕하세요! 무엇을 도와드릴까요?
          </div>
        </div>

        <div class="nova-action-badge" id="novaActionBadge">
          <span>⚡</span>
          <span id="novaActionText"></span>
        </div>

        <button class="nova-btn-talk" id="novaBtnTalk">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="22"></line>
          </svg>
          <span id="novaBtnTalkText">마이크를 탭하고 말씀하세요</span>
        </button>

        <div class="nova-quick-chips">
          <span class="nova-chip" data-cmd="1m 상자 낙하 시뮬레이션">1m 낙하</span>
          <span class="nova-chip" data-cmd="2.5m 투척 시뮬레이션">2.5m 투척</span>
          <span class="nova-chip" data-cmd="와이어프레임 토글">와이어프레임</span>
          <span class="nova-chip" data-cmd="7부품 공간 분할 보여줘">7부품 OBB</span>
          <span class="nova-chip" data-cmd="60점 레이캐스팅 정확도 평가">60점 피킹</span>
          <span class="nova-chip" data-cmd="물리 시뮬레이션 리셋">초기화</span>
          <span class="nova-chip" data-cmd="자주 묻는 질문 보여줘">FAQ</span>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    // Event Bindings
    fab.addEventListener("click", () => {
      const isHidden = modal.style.display === "none" || modal.style.display === "";
      modal.style.display = isHidden ? "flex" : "none";
    });

    document.getElementById("novaBtnClose").addEventListener("click", () => {
      modal.style.display = "none";
      stopListening();
    });

    const settingsDrawer = document.getElementById("novaSettingsDrawer");
    document.getElementById("novaBtnSettings").addEventListener("click", () => {
      settingsDrawer.style.display = settingsDrawer.style.display === "flex" ? "none" : "flex";
    });

    document.getElementById("novaBtnSaveKey").addEventListener("click", () => {
      const key = document.getElementById("novaApiKeyInput").value.trim();
      if (key) {
        state.apiKey = key;
        localStorage.setItem("OPENAI_API_KEY", key);
        document.getElementById("novaModeBadge").textContent = "OpenAI Nova";
        settingsDrawer.style.display = "none";
        alert("OpenAI API Key가 저장되었습니다! 이제 고정밀 Whisper STT 및 한국어 여성 음성(nova)으로 작동합니다.");
      }
    });

    document.getElementById("novaBtnRemoveKey").addEventListener("click", () => {
      state.apiKey = "";
      localStorage.removeItem("OPENAI_API_KEY");
      document.getElementById("novaApiKeyInput").value = "";
      document.getElementById("novaModeBadge").textContent = "브라우저 무료 모드";
      settingsDrawer.style.display = "none";
      alert("OpenAI API Key가 삭제되었습니다. 브라우저 내장 무료 모드로 전환되었습니다.");
    });

    // Talk Button Toggle
    const btnTalk = document.getElementById("novaBtnTalk");
    btnTalk.addEventListener("click", () => {
      if (state.isListening) {
        stopListening();
      } else {
        startListening();
      }
    });

    // Quick Chips click
    document.querySelectorAll(".nova-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const cmd = chip.dataset.cmd;
        updateTranscript(cmd);
        const reply = parseLocalIntent(cmd);
        updateResponse(reply);
        speakResponse(reply, null);
      });
    });
  }

  // UI State Updaters
  function updateStatus(type, label) {
    const dot = document.getElementById("novaStatusDot");
    const text = document.getElementById("novaStatusText");
    const btnText = document.getElementById("novaBtnTalkText");
    const btn = document.getElementById("novaBtnTalk");

    if (dot) {
      dot.className = "nova-status-dot";
      if (type !== "idle") dot.classList.add(type);
    }
    if (text) text.textContent = label;

    if (btn && btnText) {
      if (type === "listening") {
        btn.classList.add("recording");
        btnText.textContent = "말씀이 끝나면 탭하세요";
      } else {
        btn.classList.remove("recording");
        btnText.textContent = "마이크를 탭하고 말씀하세요";
      }
    }
  }

  function updateTranscript(text) {
    const el = document.getElementById("novaUserBubble");
    if (el) el.textContent = `🗣️ "${text}"`;
  }

  function updateResponse(text) {
    const el = document.getElementById("novaAiBubble");
    if (el) el.textContent = `✨ Nova: ${text}`;
  }

  function updateActionBadge(text) {
    const badge = document.getElementById("novaActionBadge");
    const textEl = document.getElementById("novaActionText");
    if (badge && textEl) {
      textEl.textContent = `[액션 완료] ${text}`;
      badge.style.display = "flex";
      setTimeout(() => {
        badge.style.display = "none";
      }, 5000);
    }
  }

  function startWaveAnimation() {
    const viz = document.getElementById("novaVisualizer");
    if (viz) viz.classList.add("active");
  }

  function stopWaveAnimation() {
    const viz = document.getElementById("novaVisualizer");
    if (viz) viz.classList.remove("active");
  }

  // Auto-initialize when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", createVoiceAssistantUI);
  } else {
    createVoiceAssistantUI();
  }

  // Expose global controller
  window.NovaVoiceAssistant = {
    startListening,
    stopListening,
    executeAction,
    state,
  };
})();
