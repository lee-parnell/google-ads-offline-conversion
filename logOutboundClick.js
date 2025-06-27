<script>
(function() {
    function getCookies(names) {
        var all = document.cookie.split('; ');
        var out = {};
        for (var i = 0; i < all.length; i++) {
          var pair = all[i].split('=');
          var key  = decodeURIComponent(pair[0]);
          var val  = decodeURIComponent(pair[1] || '');
          for (var j = 0; j < names.length; j++) {
            if (key === names[j]) {
              out[key] = val;
            }
          }
        }
        return out;
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
