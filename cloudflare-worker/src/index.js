export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const backendOrigin = env.BACKEND_URL || "https://tomlawa.onrender.com";
    const targetUrl = new URL(url.pathname + url.search, backendOrigin);

    const newHeaders = new Headers(request.headers);
    newHeaders.set("X-Forwarded-Host", url.host);
    newHeaders.set("X-Forwarded-Proto", url.protocol.replace(":", ""));

    const response = await fetch(targetUrl.toString(), {
      method: request.method,
      headers: newHeaders,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      redirect: "manual",
    });

    const responseHeaders = new Headers(response.headers);
    const location = responseHeaders.get("Location");
    if (location) {
      try {
        const locUrl = new URL(location, backendOrigin);
        if (locUrl.origin === new URL(backendOrigin).origin) {
          responseHeaders.set("Location", locUrl.pathname + locUrl.search);
        }
      } catch (e) {}
    }

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  },
};
