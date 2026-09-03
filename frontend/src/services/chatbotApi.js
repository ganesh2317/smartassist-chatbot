const RAW_API_URL = (import.meta.env.VITE_API_URL || "").trim();
export const API_CONFIG_ERROR = "";
const API_URL = (RAW_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const TOKEN_KEY = "smartassist_token";
const USERNAME_KEY = "smartassist_username";

export const CONNECT_ERROR = "Unable to connect to SmartAssist. Please check the backend connection.";
export class AuthError extends Error { constructor(message){ super(message); this.name="AuthError"; } }
export class ConfigError extends Error { constructor(message){ super(message); this.name="ConfigError"; } }
export const getToken = () => localStorage.getItem(TOKEN_KEY) || "";
export const getStoredUsername = () => localStorage.getItem(USERNAME_KEY) || "";
export function setSession(token, username){ localStorage.setItem(TOKEN_KEY, token); localStorage.setItem(USERNAME_KEY, username); }
export function clearSession(){ localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USERNAME_KEY); }

function requestHeaders(body, extra = {}) {
  const headers = {...extra};
  if (body !== undefined && body !== null && !(body instanceof FormData)) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function request(path, options={}){
  if(API_CONFIG_ERROR) throw new ConfigError(API_CONFIG_ERROR);
  const {skipAuthClear=false,...fetchOptions}=options;
  let response;
  try {
    response=await fetch(`${API_URL}${path}`,{
      ...fetchOptions,
      headers: requestHeaders(fetchOptions.body, fetchOptions.headers || {}),
    });
  } catch { throw new Error(CONNECT_ERROR); }

  if(!response.ok){
    let detail="Something went wrong. Please try again.";
    try{ const body=await response.json(); if(body.detail) detail=body.detail; }catch{}
    if(response.status===401 && !skipAuthClear){ clearSession(); throw new AuthError(detail); }
    throw new Error(detail);
  }
  if(response.status===204) return null;
  return response.json();
}

export const healthCheck=()=>request("/health");
export const register=(username,password)=>request("/auth/register",{method:"POST",body:JSON.stringify({username,password}),skipAuthClear:true});
export const login=(username,password)=>request("/auth/login",{method:"POST",body:JSON.stringify({username,password}),skipAuthClear:true});
export const getMe=()=>request("/auth/me");
export const listConversations=()=>request("/conversations");
export const getConversation=(id)=>request(`/conversations/${id}`);
export const deleteConversation=(id)=>request(`/conversations/${id}`,{method:"DELETE"});
export const listDocuments=()=>request("/documents");
export const deleteDocument=(id)=>request(`/documents/${id}`,{method:"DELETE"});
export function uploadDocument(file){ const body=new FormData(); body.append("file",file); return request("/documents",{method:"POST",body}); }
export function sendMessage(message,conversationId){ const body={message}; if(conversationId) body.conversation_id=conversationId; return request("/chat",{method:"POST",body:JSON.stringify(body)}); }
