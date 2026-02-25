import React, { useEffect, useMemo, useState } from "react";

const API = "http://localhost:8000";

type FeedItem = { post: { id: string; body: string; created_at: string; flags_count: number }, score: number };
type Reply = { id: string; post_id: string; body: string; created_at: string; flags_count: number; kindness_votes: number };
type DMConv = { conversation_id: string; created_at: string };
type DMMsg = { id: string; author_is_me: boolean; body: string; created_at: string };

function fmt(ts: string) {
  try { return new Date(ts).toLocaleString(); } catch { return ts; }
}

export default function App() {
  const [tab, setTab] = useState<"app"|"dm"|"admin">("app");

  // auth
  const [email, setEmail] = useState(localStorage.getItem("en_email") || "");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(localStorage.getItem("en_token") || "");

  // content
  const [postBody, setPostBody] = useState("");
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [openPostId, setOpenPostId] = useState<string | null>(null);
  const [replies, setReplies] = useState<Record<string, Reply[]>>({});
  const [replyDraft, setReplyDraft] = useState<Record<string, string>>({});
  const [toast, setToast] = useState<string>("");

  // dm
  const [convs, setConvs] = useState<DMConv[]>([]);
  const [activeConv, setActiveConv] = useState<string>("");
  const [msgs, setMsgs] = useState<DMMsg[]>([]);
  const [dmDraft, setDmDraft] = useState("");

  // admin
  const [adminToken, setAdminToken] = useState(localStorage.getItem("en_admin_token") || "");
  const [overview, setOverview] = useState<any>(null);
  const [banIp, setBanIp] = useState("");
  const [banReason, setBanReason] = useState("");

  const headers = useMemo(() => token ? { Authorization: `Bearer ${token}` } : {}, [token]);

  function flash(msg: string) {
    setToast(msg);
    window.setTimeout(() => setToast(""), 2600);
  }

  async function api<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${API}${path}`, init);
    const j = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof j === "string" ? j : JSON.stringify(j));
    return j as T;
  }

  async function register() {
    await api("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    flash("Compte créé. Connecte-toi.");
  }

  async function login() {
    const j = await api<{ access_token: string }>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    setToken(j.access_token);
    localStorage.setItem("en_token", j.access_token);
    localStorage.setItem("en_email", email);
    flash("Connecté.");
  }

  async function loadFeed() {
    const j = await api<FeedItem[]>("/feed", { headers });
    setFeed(j);
  }

  async function loadReplies(postId: string) {
    const j = await api<Reply[]>(`/posts/${postId}/replies`, { headers });
    setReplies(prev => ({ ...prev, [postId]: j }));
  }

  async function createPost() {
    await api("/posts", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify({ body: postBody }),
    });
    setPostBody("");
    await loadFeed();
    flash("Publié.");
  }

  async function sendReply(postId: string) {
    const body = (replyDraft[postId] || "").trim();
    if (!body) return;
    await api(`/posts/${postId}/reply`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify({ body }),
    });
    setReplyDraft(prev => ({ ...prev, [postId]: "" }));
    await loadReplies(postId);
    flash("Réponse envoyée.");
  }

  async function flag(target_type: "post"|"reply", target_id: string) {
    await api("/moderation/flag", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify({ target_type, target_id, reason: "abuse", details: "" }),
    });
    flash("Signalé. Merci.");
  }

  async function startDMFromPost(postId: string) {
    const j = await api<{ conversation_id: string }>("/dm/start_from_post", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify({ post_id: postId }),
    });
    setTab("dm");
    await loadDMList();
    setActiveConv(j.conversation_id);
    await loadDMMessages(j.conversation_id);
    flash("Conversation privée ouverte.");
  }

  async function loadDMList() {
    const j = await api<DMConv[]>("/dm/list", { headers });
    setConvs(j);
  }

  async function loadDMMessages(convId: string) {
    const j = await api<DMMsg[]>(`/dm/${convId}/messages`, { headers });
    setMsgs(j);
  }

  async function sendDM() {
    const body = dmDraft.trim();
    if (!body || !activeConv) return;
    await api(`/dm/${activeConv}/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify({ body }),
    });
    setDmDraft("");
    await loadDMMessages(activeConv);
  }

  async function loadAdmin() {
    const j = await api<any>("/admin/overview", { headers: { "X-Admin-Token": adminToken } });
    setOverview(j);
  }

  async function adminBanIp() {
    await api(`/moderation/ban/ip?ip=${encodeURIComponent(banIp)}&reason=${encodeURIComponent(banReason)}`, {
      method: "POST",
      headers: { "X-Admin-Token": adminToken },
    });
    flash("IP bannie.");
    setBanIp("");
    setBanReason("");
    await loadAdmin();
  }

  useEffect(() => { if (token) loadFeed(); }, [token]);

  const isAuthed = !!token;

  return (
    <>
      <div className="nav">
        <div className="nav-inner">
          <div className="brand">
            <span style={{display:"inline-flex",width:12,height:12,borderRadius:99,background:"var(--accent)"}} />
            <div>Entre Nous</div>
            <span className="badge">MVP • anonyme • sécurisé</span>
          </div>
          <div className="row">
            <button className={"btn" + (tab==="app" ? " primary" : "")} onClick={() => setTab("app")}>Fil</button>
            <button className={"btn" + (tab==="dm" ? " primary" : "")} onClick={() => { setTab("dm"); if(isAuthed) loadDMList(); }}>Privé</button>
            <button className={"btn" + (tab==="admin" ? " primary" : "")} onClick={() => setTab("admin")}>Admin</button>
            {isAuthed && (
              <button className="btn danger" onClick={() => { localStorage.removeItem("en_token"); setToken(""); setFeed([]); flash("Déconnecté."); }}>
                Déconnexion
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="container">
        {toast && <div className="toast" style={{marginBottom:14}}>{toast}</div>}

        {!isAuthed ? (
          <div className="card">
            <div className="head">
              <div className="h1">Un espace pour parler vrai.</div>
              <div className="h2">Pas de mise en scène. Pas de jugement. Une modération multi-couches.</div>
              <div className="kpi">
                <div className="pill"><span className="dot ok"/>Email chiffré</div>
                <div className="pill"><span className="dot"/>Chiffrement contenus</div>
                <div className="pill"><span className="dot warn"/>Signalement + file humaine</div>
                <div className="pill"><span className="dot bad"/>IP bans (prefix)</div>
              </div>
            </div>
            <div className="body grid">
              <div className="row">
                <input className="input" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
                <input className="input" placeholder="Mot de passe" type="password" value={password} onChange={e => setPassword(e.target.value)} />
              </div>
              <div className="row">
                <button className="btn primary" onClick={register}>Créer un compte</button>
                <button className="btn" onClick={login}>Se connecter</button>
              </div>
              <div className="small">
                L’email sert uniquement à l’accès. Stockage: chiffré + token HMAC (recherche). Anonymat absolu non garanti (dépend du déploiement).
              </div>
            </div>
          </div>
        ) : tab === "app" ? (
          <div className="grid cols">
            <div className="card">
              <div className="head">
                <div className="h1">Fil</div>
                <div className="h2">Priorité à la bienveillance, pénalisation des contenus signalés.</div>
              </div>
              <div className="body grid">
                <div className="post">
                  <div className="meta">
                    <div>Publier (anonyme)</div>
                    <div className="small">2000 caractères max</div>
                  </div>
                  <textarea className="textarea" value={postBody} onChange={e => setPostBody(e.target.value)} placeholder="Écris ce que tu n’oses pas dire ailleurs…" />
                  <div className="row" style={{marginTop:10}}>
                    <button className="btn primary" onClick={createPost}>Publier</button>
                    <button className="btn" onClick={loadFeed}>Rafraîchir</button>
                  </div>
                </div>

                <div className="grid">
                  {feed.map((it) => (
                    <div key={it.post.id} className="post">
                      <div className="meta">
                        <div>{fmt(it.post.created_at)}</div>
                        <div>score {it.score.toFixed(3)} • flags {it.post.flags_count}</div>
                      </div>
                      <div className="txt">{it.post.body}</div>
                      <div className="row" style={{marginTop:10}}>
                        <button className="btn" onClick={async() => { setOpenPostId(openPostId === it.post.id ? null : it.post.id); await loadReplies(it.post.id); }}>
                          {openPostId === it.post.id ? "Fermer" : "Réponses"}
                        </button>
                        <button className="btn" onClick={() => flag("post", it.post.id)}>Signaler</button>
                        <button className="btn primary" onClick={() => startDMFromPost(it.post.id)}>Privé</button>
                      </div>

                      {openPostId === it.post.id && (
                        <div style={{marginTop:12}}>
                          <div className="sep" />
                          <div className="grid" style={{gap:10}}>
                            {(replies[it.post.id] || []).map(r => (
                              <div key={r.id} className="reply">
                                <div className="meta">
                                  <div>{fmt(r.created_at)}</div>
                                  <div>votes {r.kindness_votes} • flags {r.flags_count}</div>
                                </div>
                                <div className="txt">{r.body}</div>
                                <div className="row" style={{marginTop:8}}>
                                  <button className="btn" onClick={() => flag("reply", r.id)}>Signaler</button>
                                </div>
                              </div>
                            ))}

                            <div className="reply">
                              <div className="meta">
                                <div>Répondre</div>
                                <div className="small">Respect + utile</div>
                              </div>
                              <textarea className="textarea" value={replyDraft[it.post.id] || ""} onChange={e => setReplyDraft(prev => ({...prev, [it.post.id]: e.target.value}))} />
                              <div className="row" style={{marginTop:10}}>
                                <button className="btn primary" onClick={() => sendReply(it.post.id)}>Envoyer</button>
                                <button className="btn" onClick={() => loadReplies(it.post.id)}>Recharger</button>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid">
              <div className="card">
                <div className="head">
                  <div className="h1">Règles</div>
                  <div className="h2">On protège les gens, pas l’ego.</div>
                </div>
                <div className="body grid">
                  <div className="pill"><span className="dot ok"/>Bienveillance obligatoire</div>
                  <div className="pill"><span className="dot warn"/>Signalement facile + auto-hide</div>
                  <div className="pill"><span className="dot"/>Chiffrement au repos</div>
                  <div className="pill"><span className="dot bad"/>Abus = bannissement (IP prefix)</div>
                  <div className="small">
                    Admin: latence, taux d’erreur, derniers signalements, décisions de modération, bans.
                  </div>
                </div>
              </div>

              <div className="card">
                <div className="head">
                  <div className="h1">Confidentialité</div>
                  <div className="h2">Minimisation. Pas de pseudo. Email chiffré.</div>
                </div>
                <div className="body grid">
                  <div className="small">
                    Pour un anonymat plus fort: désactiver les logs d’accès proxy/CDN, limiter les corrélations, et envisager Tor/Onion.
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : tab === "dm" ? (
          <div className="grid cols">
            <div className="card">
              <div className="head">
                <div className="h1">Privé</div>
                <div className="h2">Conversations chiffrées au repos.</div>
              </div>
              <div className="body grid">
                <div className="row">
                  <button className="btn" onClick={loadDMList}>Rafraîchir</button>
                  <div className="small">Ouvre une conversation depuis un post (bouton “Privé”).</div>
                </div>
                <div className="grid">
                  {convs.map(c => (
                    <button key={c.conversation_id} className={"btn" + (activeConv===c.conversation_id ? " primary" : "")}
                      onClick={async() => { setActiveConv(c.conversation_id); await loadDMMessages(c.conversation_id); }}
                      style={{justifyContent:"space-between"}}
                    >
                      <span>Conversation</span>
                      <span className="small">{fmt(c.created_at)}</span>
                    </button>
                  ))}
                  {!convs.length && <div className="small">Aucune conversation.</div>}
                </div>
              </div>
            </div>

            <div className="card">
              <div className="head">
                <div className="h1">Messages</div>
                <div className="h2">Tu peux parler sans te montrer.</div>
              </div>
              <div className="body grid">
                {!activeConv ? (
                  <div className="small">Sélectionne une conversation.</div>
                ) : (
                  <>
                    <div className="grid" style={{gap:10, maxHeight:520, overflow:"auto", paddingRight:6}}>
                      {msgs.map(m => (
                        <div key={m.id} className={"reply" + (m.author_is_me ? " right" : "")} style={{display:"flex"}}>
                          <div style={{maxWidth:"92%", width:"fit-content"}}>
                            <div className="meta" style={{justifyContent:"space-between"}}>
                              <div className="small">{m.author_is_me ? "Moi" : "Autre"}</div>
                              <div className="small">{fmt(m.created_at)}</div>
                            </div>
                            <div className="txt">{m.body}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="sep" />
                    <textarea className="textarea" value={dmDraft} onChange={e => setDmDraft(e.target.value)} placeholder="Écris un message privé…" />
                    <div className="row">
                      <button className="btn primary" onClick={sendDM}>Envoyer</button>
                      <button className="btn" onClick={() => loadDMMessages(activeConv)}>Recharger</button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="grid cols">
            <div className="card">
              <div className="head">
                <div className="h1">Admin</div>
                <div className="h2">Latences, erreurs, signalements, file, bans.</div>
              </div>
              <div className="body grid">
                <input className="input" placeholder="X-Admin-Token" value={adminToken} onChange={e => { setAdminToken(e.target.value); localStorage.setItem("en_admin_token", e.target.value); }} />
                <div className="row">
                  <button className="btn primary" onClick={loadAdmin}>Charger tableau</button>
                </div>

                {overview && (
                  <>
                    <div className="sep" />
                    <div className="kpi">
                      <div className="pill"><span className="dot"/>p50 {overview.metrics.latency_ms_p50?.toFixed?.(1) ?? "—"} ms</div>
                      <div className="pill"><span className="dot warn"/>p95 {overview.metrics.latency_ms_p95?.toFixed?.(1) ?? "—"} ms</div>
                      <div className="pill"><span className="dot ok"/>req {overview.metrics.requests_total}</div>
                      <div className="pill"><span className="dot bad"/>pending {overview.moderation.pending_count}</div>
                    </div>

                    <div className="sep" />
                    <div className="grid">
                      <div className="h2" style={{fontSize:14}}>Bannir une IP</div>
                      <div className="row">
                        <input className="input" placeholder="IP (ex: 1.2.3.4)" value={banIp} onChange={e=>setBanIp(e.target.value)} />
                        <input className="input" placeholder="Raison (optionnel)" value={banReason} onChange={e=>setBanReason(e.target.value)} />
                      </div>
                      <div className="row">
                        <button className="btn danger" onClick={adminBanIp}>Bannir</button>
                      </div>
                    </div>

                    <div className="sep" />
                    <div className="grid">
                      <div className="h2" style={{fontSize:14}}>Derniers signalements</div>
                      <div className="grid" style={{gap:10}}>
                        {overview.moderation.last_flags.map((f:any) => (
                          <div key={f.id} className="reply">
                            <div className="meta">
                              <div>{f.target_type} • {f.reason}</div>
                              <div>{fmt(f.created_at)}</div>
                            </div>
                            <div className="small">target: {f.target_id}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className="card">
              <div className="head">
                <div className="h1">Attention</div>
                <div className="h2">Ce qui “va / va pas” (MVP).</div>
              </div>
              <div className="body grid">
                <div className="pill"><span className="dot ok"/>Chiffrement DB: OK</div>
                <div className="pill"><span className="dot warn"/>Admin: pas de déchiffrement contenu par défaut</div>
                <div className="pill"><span className="dot warn"/>DM: recherche conversation O(n) (MVP)</div>
                <div className="pill"><span className="dot bad"/>IP /24 peut bloquer des innocents</div>
                <div className="small">
                  Pour scale: index pair-conversation, règles anti-spam avancées, modèle de modération IA branché, et dashboards avec séries temporelles.
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
