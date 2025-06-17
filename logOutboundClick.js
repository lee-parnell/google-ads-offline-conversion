<script>
(function() {
    var endpoint = "https://rg6u2gsl87.execute-api.eu-central-1.amazonaws.com/outbound-click-logs"; 
    var params = new URLSearchParams(window.location.search);
    var gclid = params.get("gclid");
    var gbraid = params.get("gbraid");

    if (!gclid && !gbraid) return;

    var payload = JSON.stringify({
        gclid: gclid,
        gbraid: gbraid,
        pagePath: window.location.pathname
    });
    var blob = new Blob([payload], {type: "text/plain"});

    navigator.sendBeacon(endpoint, blob);
})();
</script>
