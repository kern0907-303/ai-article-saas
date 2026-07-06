const DEFAULT_API_ORIGIN = "https://ai-article-saas.onrender.com";
const ALLOWED_METHODS = "GET,HEAD,POST,PUT,PATCH,DELETE,OPTIONS";
const ALLOWED_HEADERS = "Content-Type,Authorization,X-Admin-Key";

function corsHeaders(request) {
  const origin = request.headers.get("Origin") || "";
  return {
    "Access-Control-Allow-Origin": origin || "*",
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": ALLOWED_METHODS,
    "Access-Control-Allow-Headers": ALLOWED_HEADERS,
    "Access-Control-Max-Age": "86400",
  };
}

function targetUrl(request, env) {
  const url = new URL(request.url);
  const apiOrigin = (env.API_ORIGIN || DEFAULT_API_ORIGIN).replace(/\/+$/, "");

  if (url.pathname === "/api/healthz") {
    return `${apiOrigin}/healthz${url.search}`;
  }

  if (url.pathname === "/api/readyz") {
    return `${apiOrigin}/readyz${url.search}`;
  }

  return `${apiOrigin}${url.pathname}${url.search}`;
}

async function proxyApiRequest(request, env) {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders(request) });
  }

  const proxied = new Request(targetUrl(request, env), request);
  const response = await fetch(proxied);
  const headers = new Headers(response.headers);
  const cors = corsHeaders(request);
  Object.entries(cors).forEach(([key, value]) => headers.set(key, value));
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/")) {
      return proxyApiRequest(request, env);
    }
    return env.ASSETS.fetch(request);
  },
};
