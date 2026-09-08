import { useEffect, useState } from "react";
import { config } from "@/config";
import { systemApi } from "@/services/api/system";

type TierKey = "device" | "edge" | "cloud";
type NodeConfig = { enabled: boolean; label: string; api: string; url: string; modelName: string; capabilities: string };

const DEFAULTS: Record<TierKey, NodeConfig> = {
  device: { enabled: true, label: "本机终端", api: "ollama", url: "http://localhost:11434", modelName: "qwen2.5:0.5b", capabilities: "chat" },
  edge: { enabled: false, label: "区域边缘节点", api: "aegis_edge", url: "http://localhost:8900", modelName: "qwen2.5:7b", capabilities: "chat, reasoning" },
  cloud: { enabled: false, label: "云端推理服务", api: "openai_api", url: "https://api.openai.com/v1", modelName: "gpt-4o-mini", capabilities: "chat, reasoning, long_context" },
};

const META: Record<TierKey, { number: string; title: string; subtitle: string }> = {
  device: { number: "01", title: "端侧", subtitle: "隐私数据留在本机" },
  edge: { number: "02", title: "边侧", subtitle: "区域聚合与中型模型" },
  cloud: { number: "03", title: "云侧", subtitle: "复杂任务与长上下文" },
};
const STORAGE_KEY = "aegisos-node-config";

function readStored(): Record<TierKey, NodeConfig> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const stored = JSON.parse(raw) as Partial<Record<TierKey, Partial<NodeConfig>>>;
      // 逐 tier 深合并，防止旧本地配置吞掉默认字段（如 provider 被覆盖导致 UI 缺失）
      return (Object.keys(DEFAULTS) as TierKey[]).reduce<Record<TierKey, NodeConfig>>(
        (acc, tier) => ({ ...acc, [tier]: { ...DEFAULTS[tier], ...stored[tier] } }),
        DEFAULTS,
      );
    }
  } catch {
    // Fall back to the known demo configuration.
  }
  return DEFAULTS;
}

export function DemoSettingsView() {
  const [nodes, setNodes] = useState(DEFAULTS);
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [cloudApiKey, setCloudApiKey] = useState("");
  const [hasKey, setHasKey] = useState<boolean | null>(null);
  const [keySaving, setKeySaving] = useState(false);
  const [keyMsg, setKeyMsg] = useState<string | null>(null);

  useEffect(() => {
    setNodes(readStored());
    systemApi
      .getMode()
      .then((m) => setHasKey(m.has_key))
      .catch(() => setHasKey(null));
  }, []);

  const saveCloudApiKey = async () => {
    const key = cloudApiKey.trim();
    if (!key || keySaving) return;
    setKeySaving(true);
    setKeyMsg(null);
    try {
      const m = await systemApi.setApiKey(key);
      setHasKey(m.has_key);
      setCloudApiKey("");
      setKeyMsg(m.has_key ? "已同步到后端并即时生效，可切换 Real 模式。" : "保存完成，但后端未识别到 Key。");
    } catch (err) {
      setKeyMsg(err instanceof Error ? `保存失败：${err.message}` : "保存失败");
    } finally {
      setKeySaving(false);
    }
  };

  const update = (tier: TierKey, patch: Partial<NodeConfig>) => {
    setNodes((current) => ({ ...current, [tier]: { ...current[tier], ...patch } }));
    setStatus("idle");
  };

  const save = async () => {
    setStatus("saving");
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nodes));
    try {
      const response = await fetch("/api/v1/infra/configure", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          [config.apiKeyHeader]: config.apiKey,
        },
        body: JSON.stringify({ nodes: (Object.entries(nodes) as [TierKey, NodeConfig][]).map(([tier, node]) => ({
        node_id: tier === "device" ? "device_local" : tier === "edge" ? "edge_server_01" : "cloud_api",
        tier,
        base_url: node.url,
        provider: node.api,
        model_id: node.modelName,
        capabilities: node.capabilities.split(",").map((item) => item.trim()).filter(Boolean),
        enabled: node.enabled,
        })) }),
      });
      if (!response.ok) throw new Error(`配置保存失败: HTTP ${response.status}`);
      setStatus("saved");
    } catch {
      setStatus("error");
    }
  };

  const reset = () => {
    setNodes(DEFAULTS);
    localStorage.removeItem(STORAGE_KEY);
    setStatus("idle");
  };

  return (
    <section className="view settings-view">
      <header className="settings-hero">
        <div>
          <span className="eyebrow">RUNTIME CONTROL / LOCAL DEMO</span>
          <h2 className="settings-hero__title">端边云配置</h2>
          <p className="settings-hero__desc">为每一层设置 API、API URL、Model name 和能力标签。</p>
        </div>
        <div className="settings-hero__status"><span className="settings-hero__pulse" />{Object.values(nodes).filter((node) => node.enabled).length} 个节点启用</div>
      </header>
      <div className="settings-actions">
        <span className="settings-actions__hint">保存后立即同步到本地演示调度器</span>
        <div className="settings-actions__buttons">
          <button type="button" className="settings-button settings-button--quiet" onClick={reset}>恢复默认</button>
          <button type="button" className="settings-button settings-button--primary" onClick={() => void save()} disabled={status === "saving"}>{status === "saving" ? "保存中..." : status === "saved" ? "已保存" : status === "error" ? "保存失败" : "保存配置"}</button>
        </div>
      </div>
      <div className="settings-grid">
        {(Object.keys(META) as TierKey[]).map((tier) => {
          const node = nodes[tier];
          const meta = META[tier];
          return <article className={`node-config node-config--${tier}`} key={tier}>
            <div className="node-config__header"><div className="node-config__identity"><span className="node-config__index">{meta.number}</span><div><h3>{meta.title}</h3><p>{meta.subtitle}</p></div></div><label className="switch" title={`${meta.title}启用状态`}><input type="checkbox" checked={node.enabled} onChange={(event) => update(tier, { enabled: event.target.checked })} /><span className="switch__track" /></label></div>
            <div className="node-config__fields">
              <label><span>显示名称</span><input value={node.label} onChange={(event) => update(tier, { label: event.target.value })} /></label>
              <label className="node-config__field--wide"><span>API URL</span><input value={node.url} onChange={(event) => update(tier, { url: event.target.value })} /></label>
              <label><span>API / Provider</span><select value={node.api} onChange={(event) => update(tier, { api: event.target.value })}><option value="ollama">Ollama</option><option value="aegis_edge">Aegis Edge</option><option value="openai_api">OpenAI API</option></select></label>
              <label><span>Model name</span><input value={node.modelName} onChange={(event) => update(tier, { modelName: event.target.value })} /></label>
              <label className="node-config__field--wide"><span>能力标签</span><input value={node.capabilities} onChange={(event) => update(tier, { capabilities: event.target.value })} /></label>
            </div>
            {node.api === "openai_api" && (
              <div className="node-config__apikey">
                <div className="node-config__apikey-head">
                  <span>OpenAI 兼容 API Key（DeepSeek / OpenAI）</span>
                  <span className={`badge badge--${hasKey === null ? "pending" : hasKey ? "succeeded" : "cancelled"}`}>
                    {hasKey === null ? "查询中…" : hasKey ? "已配置" : "未配置"}
                  </span>
                </div>
                <div className="node-config__apikey-row">
                  <input
                    type="password"
                    placeholder={hasKey ? "已配置 Key，输入新 Key 覆盖" : "sk-…"}
                    value={cloudApiKey}
                    onChange={(e) => setCloudApiKey(e.target.value)}
                    aria-label="API Key"
                  />
                  <button
                    type="button"
                    className="settings-button settings-button--primary"
                    onClick={() => void saveCloudApiKey()}
                    disabled={keySaving || !cloudApiKey.trim()}
                  >
                    {keySaving ? "同步中…" : "同步到后端"}
                  </button>
                </div>
                {keyMsg ? <p className="node-config__apikey-msg">{keyMsg}</p> : null}
              </div>
            )}
            <footer className="node-config__footer"><span className={`node-config__dot${node.enabled ? " node-config__dot--on" : ""}`} /><span>{node.enabled ? "参与任务调度" : "已停用"}</span><code>{tier}</code></footer>
          </article>;
        })}
      </div>
      <div className="settings-note"><span className="settings-note__mark">i</span><p>任一层卡片选择 <code>OpenAI API</code> 时会出现 API Key 输入框；Key 全局共享，同步后写入 <code>tooling/configs/.env</code> 并即时生效。自部署 Ollama 走 URL 直连（<code>http://&lt;IP&gt;:11434/v1</code>），默认无需 Key。</p></div>
    </section>
  );
}
