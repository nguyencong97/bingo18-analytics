/**
 * Cloudflare Worker Reverse Proxy cho Vietlott Bingo18 AjaxPro API.
 */

export default {
  async fetch(request, env, ctx) {
    // 1. Hỗ trợ CORS Preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, X-AjaxPro-Method, Authorization",
          "Access-Control-Max-Age": "86400"
        }
      });
    }

    // 2. Health check endpoint (GET /)
    if (request.method === "GET") {
      return new Response(
        JSON.stringify({
          status: "ok",
          service: "Vietlott Bingo18 Cloudflare Edge Proxy",
          timestamp: new Date().toISOString()
        }),
        {
          headers: {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": "*"
          }
        }
      );
    }

    // 3. Xử lý POST request tới Vietlott AjaxPro
    const TARGET_URL = "https://vietlott.vn/ajaxpro/Vietlott.PlugIn.WebParts.GameBingoCompareWebPart,Vietlott.PlugIn.WebParts.ashx";

    try {
      const requestBody = await request.text();

      const forwardHeaders = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Content-Type": "text/plain; charset=utf-8",
        "X-AjaxPro-Method": "ServerSideDrawResult",
        "Origin": "https://vietlott.vn",
        "Referer": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/winning-number-bingo18",
        "Accept": "*/*",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
      };

      const response = await fetch(TARGET_URL, {
        method: "POST",
        headers: forwardHeaders,
        body: requestBody
      });

      const responseBody = await response.text();

      return new Response(responseBody, {
        status: response.status,
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "no-store"
        }
      });
    } catch (error) {
      return new Response(
        JSON.stringify({ error: true, message: error.toString() }),
        {
          status: 502,
          headers: {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": "*"
          }
        }
      );
    }
  }
};
