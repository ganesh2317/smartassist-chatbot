const time=t=>{try{return new Date(t).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})}catch{return ""}};
export default function Message({message}){
  const user=message.role==="user";
  return <article className={`message-row ${user?"user":"bot"}`}>
    <div className="avatar">{user?"You":"AI"}</div>
    <div className="message-content">
      <p className="bubble">{message.content}</p>
      {message.sources?.length>0 && <div className="source-list" aria-label="Knowledge sources">
        {message.sources.map(source=><div className="source-card" key={source.document_id}>
          <strong>{source.name}</strong><span>{source.excerpt}{source.excerpt?.length>=220?"…":""}</span>
        </div>)}
      </div>}
      <small>{time(message.timestamp)}</small>
    </div>
  </article>;
}
