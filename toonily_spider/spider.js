// ==UserScript==
// @name         toonily spider
// @namespace    obgnail
// @version      0.1
// @author       obgnail
// @match        https://toonily.com/webtoon/*
// @icon         https://www.google.com/s2/favicons?domain=toonily.com
// @grant        GM.xmlHttpRequest
// @run-at       document-body
// ==/UserScript==


(function () {
    'use strict';
    const DEFAULT_HEADERS = {
        "referer": "https://toonily.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
    }

    let getXmlHttpRequest = () => {
        return (typeof GM !== "undefined" && GM !== null ? GM.xmlHttpRequest : GM_xmlhttpRequest);
    }

    let insertDownloadButton = () => {
        const links = document.getElementById("init-links");
        if (links === null) {
            return
        }

        const button = document.createElement("a");
        button.id = "btn-read-download"
        button.className = "c-btn c-btn_style-1";
        button.href = "javascript:;"
        button.innerHTML = "download";
        button.addEventListener("click", download)

        links.appendChild(button);
    }

    let request = (url, responseType, callback) => {
        getXmlHttpRequest()({
            method: "GET",
            url: url,
            responseType: responseType,
            headers: DEFAULT_HEADERS,
            onload: resp => {
                if (resp.readyState === 4 && resp.status === 200) {
                    callback(resp)
                } else if (resp.readyState === 4 && resp.status === 404) {
                    callback(null)
                }
            },
            onerror: resp => {
                console.log("request on error", url)
            },
            ontimeout: resp => {
                console.log("request on timeout", url)
            }
        });
    }

    let defaultRequest = (url, callback) => request(url, "text", callback)

    let requestImage = (url, fileName) => {
        console.log("prepare download:", fileName, url)

        request(url, "blob", resp => {
            if (resp === null) {
                console.log("request image err")
                return
            }
            const link = document.createElement('a');
            link.href = window.URL.createObjectURL(resp.response);
            link.download = fileName;
            link.click();
        })
    }

    let download = () => {
        defaultRequest(window.location.href, resp => {
            if (resp === null) {
                console.log("request chapters error")
                return
            }
            const dom = new DOMParser().parseFromString(resp.responseText, "text/html");
            const chapters = parseFirstPage(dom);

            // let temp = [chapters[0], chapters[1]]
            // downloadChapterImages(temp); // todo
            downloadChapterImages(chapters);
        })
    }

    let parseFirstPage = (dom) => {
        let chapters = []
        const content = dom.querySelectorAll("#manga-content-tabs .listing-chapters_wrap .wp-manga-chapter a")

        for (let i = content.length - 1; i >= 0; i--) {
            chapters.push({
                "name": content[i].innerHTML.trim(),
                "url": content[i].getAttribute("href"),
            })
        }
        return chapters
    }

    let downloadChapterImages = (chapters) => {
        if (chapters === null || chapters.length === 0) {
            console.log("chapters is null")
            return
        }
        chapters.forEach(ele => downloadChapterImage(ele))
    }

    let downloadChapterImage = (chapter) => {

        defaultRequest(chapter.url, resp => {
            const dom = new DOMParser().parseFromString(resp.responseText, "text/html");
            let images = parseDetailPath(dom);

            images.forEach(ele => {
                requestImage(ele.url, chapter.name + "-" + ele.name)
            })
        })
    }

    let parseDetailPath = (dom) => {
        let images = []
        const content = dom.querySelectorAll(".read-container .reading-content img")
        content.forEach(ele => {
            images.push({
                "name": ele.getAttribute("id"),
                "url": ele.getAttribute("data-src").trim(),
            })
        })
        return images
    }


    insertDownloadButton()
})();