// ==UserScript==
// @name         Instagram RSS Feed URL
// @namespace    https://www.instagram.com
// @version      1.1
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

function fetch_user_id(profile_name, callback) {
    const userUrl = `https://www.instagram.com/api/v1/users/web_profile_info/?username=${profile_name}`;

    fetch(userUrl, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Instagram 273.0.0.16.70 (iPad13,8; iOS 16_3; en_US; en-US; scale=2.00; 2048x2732; 452417278) AppleWebKit/420+'
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch user data');
            }
            return response.json();
        })
        .then(data => {
            const userId = data?.data?.user?.id || null;
            callback(userId);
        })
        .catch(error => {
            console.error('Error fetching user ID:', error);
            callback(null);
        });
}

setTimeout(function () {
    $(document).ready(function () {
        let profile_name = get_profile_name();
        console.log("instagram_rss for " + profile_name);
        if (!profile_name) {
            return;
        }

        let profileLink = document.querySelector('a[href="/"][role="link"]');

        if (profileLink) {
            fetch_user_id(profile_name, function (userId) {
                const rssUrl = `${urlBase}/${profile_name}`;

                const rssLink = document.createElement('a');
                rssLink.href = rssUrl;

                rssLink.innerText = userId ? userId : 'RSS';

                rssLink.style.marginLeft = '10px';
                rssLink.style.fontWeight = 'bold';
                rssLink.style.color = '#3897f0';

                profileLink.parentNode.insertBefore(rssLink, profileLink.nextSibling);
            });
        }
    });
}, 3000);
