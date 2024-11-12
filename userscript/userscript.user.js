// ==UserScript==
// @name         Instagram RSS Feed URL
// @namespace    https://www.instagram.com
// @version      1.0
// @description  Add Instagram RSS Feed URL Button
// @author       Alexey ALERT Rubasheff
// @homepageURL  https://github.com/ALERTua/instagram_rss/blob/main/userscript/userscript.user.js
// @source       https://github.com/ALERTua/instagram_rss/raw/refs/heads/main/userscript/userscript.user.js
// @match        *://www.instagram.com/*
// @require http://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js
// ==/UserScript==

/* global Chart */
/* eslint-disable no-multi-spaces, no-return-assign */
'use strict';

const urlBase = "https://instagramrss.alertua.duckdns.org/instagram";

function get_profile_name() {
    let urlParts = window.location.pathname.split('/');
    let profileName = urlParts[1];
    return profileName;
}



// Add delay before executing the code
setTimeout(function() {
    $(document).ready(function () {
        let profile_name = get_profile_name();
        console.log("instagram_rss for " + profile_name);
        if (!profile_name) {
            return;
        }

        let profileLink = document.querySelector('a[href="/"][role="link"]');

        if (profileLink) {
            // Construct the RSS URL
            const rssUrl = `${urlBase}/${profile_name}`;

            // Create the RSS link element
            const rssLink = document.createElement('a');
            rssLink.href = rssUrl;
            rssLink.innerText = 'RSS';
            rssLink.style.marginLeft = '10px'; // Adjust margin if necessary
            rssLink.style.fontWeight = 'bold';
            rssLink.style.color = '#3897f0'; // Instagram-like color for consistency

            // Append the RSS link next to the profile link
            profileLink.parentNode.insertBefore(rssLink, profileLink.nextSibling);
        }
    });
}, 3000); // Delay in milliseconds
