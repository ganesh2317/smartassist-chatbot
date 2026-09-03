import {useEffect,useState} from "react";
import Header from "./components/Header.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import MessageInput from "./components/MessageInput.jsx";
import LoginPage from "./components/LoginPage.jsx";
import ConversationList from "./components/ConversationList.jsx";
import KnowledgePanel from "./components/KnowledgePanel.jsx";
import {
  AuthError,clearSession,deleteConversation,deleteDocument,getConversation,getMe,getStoredUsername,getToken,
  healthCheck,listConversations,listDocuments,sendMessage,setSession,uploadDocument,
} from "./services/chatbotApi.js";

const msg=(role,content,timestamp,sources=[])=>({role,content,timestamp:timestamp||new Date().toISOString(),sources});
const welcome=()=>[msg("bot","Hello! I'm SmartAssist. Ask a general question, or open Knowledge and drop in your own files so I can answer from them.")];

export default function App(){
  const [authReady,setAuthReady]=useState(false);
  const [username,setUsername]=useState(getStoredUsername);
  const [messages,setMessages]=useState(welcome);
  const [conversations,setConversations]=useState([]);
  const [conversationId,setConversationId]=useState(null);
  const [historyOpen,setHistoryOpen]=useState(false);
  const [knowledgeOpen,setKnowledgeOpen]=useState(false);
  const [documents,setDocuments]=useState([]);
  const [uploading,setUploading]=useState(false);
  const [documentError,setDocumentError]=useState("");
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const [status,setStatus]=useState("checking");
  const [aiConfigured,setAiConfigured]=useState(null);
  const isLoggedIn=Boolean(username&&getToken());

  const refreshConversations=async()=>{const items=await listConversations();setConversations(items);return items;};
  const refreshDocuments=async()=>{const items=await listDocuments();setDocuments(items);return items;};
  const authFail=e=>{if(e instanceof AuthError){setUsername("");setConversations([]);setDocuments([]);setConversationId(null);setMessages(welcome());setError("");return true;}return false;};

  useEffect(()=>{let active=true;const check=async()=>{try{const health=await healthCheck();if(active){setStatus("online");setAiConfigured(Boolean(health.ai_configured));}}catch{if(active){setStatus("offline");setAiConfigured(null);}}};check();const timer=setInterval(check,30000);return()=>{active=false;clearInterval(timer);};},[]);
  useEffect(()=>{(async()=>{if(!getToken()){setAuthReady(true);return;}try{const me=await getMe();setUsername(me.username);setSession(getToken(),me.username);await Promise.all([refreshConversations(),refreshDocuments()]);}catch(e){if(e instanceof AuthError){clearSession();setUsername("");}else if(!getStoredUsername()){clearSession();setUsername("");}}finally{setAuthReady(true);}})();},[]);

  const handleLoggedIn=data=>{setSession(data.access_token,data.username);setUsername(data.username);setMessages(welcome());setConversationId(null);setError("");Promise.all([refreshConversations(),refreshDocuments()]).catch(()=>{});};
  const logout=()=>{clearSession();setUsername("");setConversations([]);setDocuments([]);setConversationId(null);setMessages(welcome());setHistoryOpen(false);setKnowledgeOpen(false);setError("");};
  const newChat=()=>{setConversationId(null);setMessages(welcome());setError("");setHistoryOpen(false);};
  const select=async id=>{try{const data=await getConversation(id);setConversationId(data.id);setMessages(data.messages?.length?data.messages:welcome());setError("");setHistoryOpen(false);}catch(e){if(!authFail(e))setError(e.message||"Unable to load that conversation.");}};
  const del=async id=>{if(!window.confirm("Delete this conversation? This cannot be undone."))return;try{await deleteConversation(id);await refreshConversations();if(conversationId===id)newChat();}catch(e){if(!authFail(e))setError(e.message||"Unable to delete that conversation.");}};

  const send=async text=>{setMessages(current=>[...current,msg("user",text)]);setLoading(true);setError("");try{const data=await sendMessage(text,conversationId);setMessages(current=>[...current,msg("bot",data.reply,undefined,data.sources||[])]);setConversationId(data.conversation_id);try{await refreshConversations();}catch{setError("Message sent, but the chat list could not refresh. Your message is still saved.");}}catch(e){if(!authFail(e))setError(e.message||"Unable to send your message.");}finally{setLoading(false);}};

  const upload=async files=>{setUploading(true);setDocumentError("");const failures=[];for(const file of files){try{await uploadDocument(file);}catch(e){failures.push(`${file.name}: ${e.message}`);if(authFail(e))break;}}try{await refreshDocuments();}catch{}if(failures.length)setDocumentError(failures.join(" "));setUploading(false);};
  const removeDoc=async(id,name)=>{if(!window.confirm(`Delete ${name} from SmartAssist knowledge?`))return;setDocumentError("");try{await deleteDocument(id);await refreshDocuments();}catch(e){if(!authFail(e))setDocumentError(e.message||"Unable to delete that document.");}};

  if(!authReady)return <div className="boot-screen">Loading SmartAssist...</div>;
  if(!isLoggedIn)return <LoginPage onLoggedIn={handleLoggedIn}/>;
  return <div className="app-shell">
    <div className="app-layout">
      <ConversationList conversations={conversations} selectedId={conversationId} onSelect={select} onNewChat={newChat} onDelete={del} open={historyOpen}/>
      <div className="chat-card">
        <Header username={username} onLogout={logout} onToggleHistory={()=>{setHistoryOpen(v=>!v);setKnowledgeOpen(false)}} historyOpen={historyOpen} onToggleKnowledge={()=>{setKnowledgeOpen(v=>!v);setHistoryOpen(false)}} knowledgeOpen={knowledgeOpen} documentCount={documents.length} status={status} aiConfigured={aiConfigured}/>
        <ChatWindow messages={messages} loading={loading} error={error}/>
        <MessageInput onSend={send} disabled={loading}/>
      </div>
      <KnowledgePanel open={knowledgeOpen} documents={documents} onUpload={upload} onDelete={removeDoc} uploading={uploading} error={documentError} onClose={()=>setKnowledgeOpen(false)}/>
    </div>
    {(historyOpen||knowledgeOpen)&&<button className="drawer-backdrop" aria-label="Close open panel" onClick={()=>{setHistoryOpen(false);setKnowledgeOpen(false)}}/>}
  </div>;
}
