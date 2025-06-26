<script>
(function() {
    function getCookies(trackingCookieNames){
        var cookies = document.cookie 
            .split('; ')
            .map(pair => pair.split('='))
            .map(([key, val]) => [decodeURIComponent(key), decodeURIComponent(val)])
            .filter(([key]) => trackingCookieNames.includes(key));
        return Object.fromEntries(cookies)
    }

    var endpoint = "https:/YOUR_LAMBDA_API_GATEWAY_URL/outbound-click-logs"; 

    var params = new URLSearchParams(window.location.search);
    var gclid = params.get("gclid");
    var gbraid = params.get("gbraid");
    
    var cookies = getCookies(['_ads_gclid', '_ads_gbraid'])

    if ((!gclid && !gbraid) || Object.keys(cookies).length == 0) return;

    var payload = JSON.stringify({
        gclid: gclid || cookies['_ads_gclid'],
        gbraid: gbraid || cookies['_ads_gbraid'],
        pagePath: window.location.pathname
    });
    var blob = new Blob([payload], {type: "text/plain"});

    navigator.sendBeacon(endpoint, blob);
})();
</script>
