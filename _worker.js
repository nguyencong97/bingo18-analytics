/**
 * Cloudflare Pages Advanced Mode _worker.js
 * 
 * 1. Nếu là POST request (Crawler / Render / Google Apps Script gọi):
 *    Chuyển tiếp đến cổng Vietlott AjaxPro với đầy đủ Header Chrome để vượt tường lửa.
 * 2. Nếu là GET request thông thường của người dùng:
 *    Phục vụ ứng dụng React web app (env.ASSETS).
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 1. Xử lý CORS Preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
          "Access-Control-Allow-Headers": "*",
          "Access-Control-Max-Age": "86400"
        }
      });
    }

    // 2. Nếu là POST request hoặc có header X-AjaxPro-Method hoặc đường dẫn proxy/ajaxpro
    const isAjaxPro = request.headers.get("x-ajaxpro-method") || 
                      url.pathname.includes("ajaxpro") || 
                      url.pathname.includes("proxy");

    if (request.method === "POST" || isAjaxPro) {
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
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
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

    // 3. Nếu là GET thông thường: Phục vụ ứng dụng React tĩnh
    if (env && env.ASSETS && typeof env.ASSETS.fetch === "function") {
      return env.ASSETS.fetch(request);
    }

    return new Response(
      JSON.stringify({ status: "ok", service: "Vietlott Bingo18 Edge Proxy" }),
      {
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*"
        }
      }
    );
  }
};
