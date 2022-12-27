package main

import (
	"flag"
	"fmt"
	"github.com/juju/errors"
	"github.com/sirupsen/logrus"
	"io/ioutil"
	"net/http"
	URL "net/url"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	shardFileFormat = "%05d.ts"
)

const (
	KB = 1024
	MB = 1024 * 1024
	GB = 1024 * 1024 * 1024
)

var Logger *logrus.Logger

func init() {
	Logger = &logrus.Logger{
		Out:   os.Stderr,
		Level: logrus.DebugLevel,
		Formatter: &logrus.TextFormatter{
			ForceColors:               true,
			EnvironmentOverrideColors: true,
			DisableQuote:              true,
			DisableLevelTruncation:    true,
			FullTimestamp:             true,
			TimestampFormat:           "15:04:05",
		},
	}
}

type WaitGroup struct {
	wg sync.WaitGroup
	p  chan struct{}
}

func NewWaitGroup(parallel int) (w *WaitGroup) {
	w = &WaitGroup{}
	if parallel <= 0 {
		return
	}
	w.p = make(chan struct{}, parallel)
	return
}

func (w *WaitGroup) AddDelta() {
	w.wg.Add(1)
	if w.p == nil {
		return
	}
	w.p <- struct{}{}
}

func (w *WaitGroup) Done() {
	w.wg.Done()
	if w.p == nil {
		return
	}
	<-w.p
}

func (w *WaitGroup) Wait() {
	w.wg.Wait()
}

func (w *WaitGroup) Parallel() int {
	return len(w.p)
}

type ProcessBar struct {
	mu        sync.Mutex // protect current and load()
	graph     string     // 显示符号
	start     int        // 开始的进度位置
	current   int        // 当前的进度位置
	total     int        // 总进度
	bytes     uint64     // 总字节数
	startTime time.Time  // 开始时间
	_once     sync.Once
}

func NewBar(current, total int) *ProcessBar {
	bar := &ProcessBar{graph: "█", total: total}
	bar.reset(current)
	return bar
}

func (b *ProcessBar) Add(bytes uint64) {
	b.withLock(func() {
		b.current += 1
		b.bytes += bytes
		if b.current > b.total {
			b.current = b.total
		}
		b.load()
	})
}

func (b *ProcessBar) Reset(current int) {
	b.withLock(func() {
		b.reset(current)
		b.load()
	})
}

func (b *ProcessBar) Start() {
	b._once.Do(func() {
		go func() {
			for b.current < b.total {
				b.withLock(b.load)
				time.Sleep(time.Second)
			}
		}()
	})
}

func (b *ProcessBar) withLock(f func()) {
	b.mu.Lock()
	f()
	b.mu.Unlock()
}

func (b *ProcessBar) reset(current int) {
	if current > b.total {
		current = b.total
	}
	b.start = current
	b.current = current
	b.bytes = 0
	b.startTime = time.Now()
}

func (b *ProcessBar) getPercent() int {
	return int((float64(b.current) / float64(b.total)) * 100)
}

func toTimeString(second float64) string {
	str := ""
	h := int(second) / 3600
	m := int(second) % 3600 / 60
	if h > 0 {
		str += strconv.Itoa(h) + "h "
	}
	if h > 0 || m > 0 {
		str += strconv.Itoa(m) + "m "
	}
	str += strconv.Itoa(int(second)%60) + "s"
	return str
}

func (b *ProcessBar) toSizeString(fileSize uint64) string {
	switch {
	case fileSize < KB:
		return fmt.Sprintf("%.2fB", float64(fileSize))
	case fileSize < MB:
		return fmt.Sprintf("%.2fKB", float64(fileSize)/KB)
	case fileSize < GB:
		return fmt.Sprintf("%.2fMB", float64(fileSize)/MB)
	default:
		return fmt.Sprintf("%.2fGB", float64(fileSize)/GB)
	}
}

func (b *ProcessBar) getTransferRate() string {
	spent := uint64(time.Now().Sub(b.startTime).Seconds())
	if spent == 0 {
		return "0B/s"
	}
	size := b.toSizeString(b.bytes / spent)
	return fmt.Sprintf("%s/s", size)
}

func (b *ProcessBar) getTotalTransferSize() string {
	return b.toSizeString(b.bytes)
}

func (b *ProcessBar) getSpentTime() string {
	u := time.Now().Sub(b.startTime).Seconds()
	return toTimeString(u)
}

func (b *ProcessBar) getRemainTime() string {
	process := b.current - b.start
	if process == 0 {
		return "INF"
	}
	spent := time.Now().Sub(b.startTime).Seconds()
	remain := b.total - b.current
	u := spent * float64(remain) / float64(process)
	return toTimeString(u)
}

// need lock
func (b *ProcessBar) load() {
	percent := b.getPercent()
	spent := b.getSpentTime()
	remain := b.getRemainTime()
	transferRate := b.getTransferRate()
	totalTransfer := b.getTotalTransferSize()
	bar := strings.Repeat(b.graph, percent/2)

	fmt.Printf("\r[%-50s]% 3d%%(%d/%d)    %2s(%2s)    %2s(+%2s)        ",
		bar, percent, b.current, b.total, totalTransfer, transferRate, spent, remain)

	if b.current == b.total {
		fmt.Println()
	}
}

type M3u8Downloader struct {
	url          string
	downPath     string
	savePath     string
	saveName     string
	clearDebris  bool
	threads      uint
	maxRetry     uint
	isShardFunc  func(line string) (need bool)                         // 有些网站会在视频中插入广告shard,用此过滤
	fixShardFunc func(shard string, m3u8Url string) string             // 有些网站不严格遵守m3u8,自定义拼接url,用此纠错
	requestFunc  func(url string) (*http.Client, *http.Request, error) // 有些网站有反爬措施,用此自定义参数
	_totalShard  int
	_encrypt     bool
	_bar         *ProcessBar
}

func New(url, saveName, downPath, savePath string, clearDebris bool, threads, maxRetry uint,
	isShardFunc func(line string) (need bool),
	fixShardFunc func(shard string, m3u8Url string) string,
	requestFunc func(url string) (*http.Client, *http.Request, error),
) *M3u8Downloader {
	if len(saveName) == 0 {
		u, err := URL.Parse(url)
		if err != nil {
			panic(err)
		}
		result := strings.Split(u.Path, "/")
		saveName = fmt.Sprintf("%s.ts", result[len(result)-1])
	}
	if len(downPath) == 0 {
		downPath = "./Download"
	}
	downPath = filepath.Join(downPath, saveName)

	if len(savePath) == 0 {
		savePath = "./Complete"
	}

	d := &M3u8Downloader{
		url:         url,
		saveName:    saveName,
		downPath:    downPath,
		savePath:    savePath,
		clearDebris: clearDebris,
		threads:     threads,
		maxRetry:    maxRetry,
		_encrypt:    false,
	}
	d.SetIsShardFunc(isShardFunc)
	d.SetFixShardFunc(fixShardFunc)
	d.SetRequestFunc(requestFunc)
	return d
}

func (d *M3u8Downloader) SetIsShardFunc(isShardFunc func(line string) (need bool)) {
	if isShardFunc == nil {
		isShardFunc = func(line string) (need bool) { return !strings.HasPrefix(line, "#") }
	}
	d.isShardFunc = isShardFunc
}

func (d *M3u8Downloader) SetFixShardFunc(fixShardFunc func(shard string, m3u8Url string) string) {
	if fixShardFunc == nil {
		fixShardFunc = func(shard string, m3u8Url string) string {
			list := strings.Split(m3u8Url, "/")
			baseUrl := strings.Join(list[:len(list)-1], "/")
			if !strings.HasPrefix(shard, "http") {
				shard = baseUrl + "/" + shard
			}
			return shard
		}
	}
	d.fixShardFunc = fixShardFunc
}

func (d *M3u8Downloader) SetRequestFunc(requestFunc func(url string) (*http.Client, *http.Request, error)) {
	if requestFunc == nil {
		requestFunc = func(url string) (*http.Client, *http.Request, error) {
			req, _ := http.NewRequest("GET", url, nil)
			u, err := URL.Parse(url)
			if err != nil {
				return nil, nil, errors.Trace(err)
			}
			s := fmt.Sprintf("%s://%s", u.Scheme, u.Host)
			req.Header.Set("origin", s)
			req.Header.Set("referer", s)
			req.Header.Set("Host", u.Host)
			req.Header.Set("user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "+
				"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
			return &http.Client{}, req, nil
		}
	}
	d.requestFunc = requestFunc
}

func getFileMap(dirPath string) (map[string]struct{}, error) {
	files, err := ioutil.ReadDir(dirPath)
	if err != nil {
		return nil, errors.Trace(err)
	}
	fileMap := make(map[string]struct{})
	for _, f := range files {
		fileMap[f.Name()] = struct{}{}
	}
	return fileMap, nil
}

func (d *M3u8Downloader) filter(shards map[int]string) (map[int]string, error) {
	fileMap, err := getFileMap(d.downPath)
	if err != nil {
		return nil, errors.Trace(err)
	}
	for idx := 0; idx < d._totalShard; idx++ {
		fileName := fmt.Sprintf(shardFileFormat, idx)
		if _, ok := fileMap[fileName]; ok {
			delete(shards, idx)
		}
	}
	return shards, nil
}

func (d *M3u8Downloader) done() (bool, error) {
	fileMap, err := getFileMap(d.downPath)
	if err != nil {
		return false, errors.Trace(err)
	}
	for idx := 0; idx < d._totalShard; idx++ {
		fileName := fmt.Sprintf(shardFileFormat, idx)
		if _, ok := fileMap[fileName]; !ok {
			return false, nil
		}
	}
	return true, nil
}

func (d *M3u8Downloader) check(url string) bool {
	return strings.HasPrefix(url, "http")
}

func (d *M3u8Downloader) request(url string) (body []byte, err error) {
	client, req, err := d.requestFunc(url)
	if err != nil {
		return nil, errors.Trace(err)
	}
	resp, err := client.Do(req)
	if err != nil {
		return nil, errors.Trace(err)
	}
	defer resp.Body.Close()

	body, err = ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, errors.Trace(err)
	}
	if resp.StatusCode != 200 {
		return body, fmt.Errorf("resp.statusCode == %d", resp.StatusCode)
	}
	return
}

func (d *M3u8Downloader) parseM3u8Url(m3u8Url string, isShardFunc func(line string) (need bool)) (
	shards []string, err error) {
	if isShardFunc == nil {
		panic("isShardFunc == nil")
	}
	resp, err := d.request(m3u8Url)
	if err != nil {
		return nil, errors.Trace(err)
	}
	response := strings.Split(string(resp), "\n")

	for _, line := range response {
		line = strings.TrimSpace(line)
		if len(line) == 0 {
			continue
		}
		if isShardFunc(line) == true {
			shards = append(shards, line)
		}
		if strings.HasPrefix(line, "#EXT-X-KEY:") {
			d._encrypt = true
		}
	}
	if len(shards) == 0 {
		return nil, fmt.Errorf("len(shards) == 0")
	}
	return
}

func mkdir(Path string) error {
	if _, err := os.Stat(Path); os.IsNotExist(err) {
		if err = os.MkdirAll(Path, os.ModePerm); err != nil {
			return errors.Trace(err)
		}
	}
	return nil
}

func (d *M3u8Downloader) mkdir() (err error) {
	if err = mkdir(d.downPath); err != nil {
		return errors.Trace(err)
	}
	if err = mkdir(d.savePath); err != nil {
		return errors.Trace(err)
	}
	return
}

func writeFile(Path string, content []byte) (err error) {
	file, err := os.OpenFile(Path, os.O_WRONLY|os.O_CREATE, 0666)
	if err != nil {
		return errors.Trace(err)
	}
	defer file.Close()
	if _, err = file.Write(content); err != nil {
		return errors.Trace(err)
	}
	return
}

func (d *M3u8Downloader) downloadShard(wg *WaitGroup, shardIdx int, shardUrl, downPath string) error {
	defer wg.Done()

	debrisName := path.Join(downPath, fmt.Sprintf(shardFileFormat, shardIdx))
	if _, err := os.Stat(debrisName); os.IsNotExist(err) {
		resp, err := d.request(shardUrl)
		if err != nil {
			Logger.Errorf("shard %d failed: %s", shardIdx, shardUrl)
			return errors.Trace(err)
		}
		if err = writeFile(debrisName, resp); err != nil {
			return errors.Trace(err)
		}
		d._bar.Add(uint64(len(resp)))
	}
	return nil
}

func (d *M3u8Downloader) downloadShards(shards map[int]string, downPath string) {
	wg := NewWaitGroup(int(d.threads))
	for shardIdx, shardUrl := range shards {
		wg.AddDelta()
		go errHandler(d.downloadShard(wg, shardIdx, shardUrl, downPath))
	}
	wg.Wait()
}

func (d *M3u8Downloader) retry(maxRetry uint, f func() (stop bool, err error)) error {
	count := uint(0)
	for {
		stop, err := f()
		if stop || err != nil {
			return err
		}
		count++
		if count == maxRetry+1 {
			return fmt.Errorf("retry too much")
		}
		Logger.Warnf("[%d] Time(s) Retry...", count)
	}
}

func (d *M3u8Downloader) prepare() error {
	Logger.Debugf("[STEP0] check url")

	if !d.check(d.url) {
		return fmt.Errorf("error url: %s", d.url)
	}
	if err := d.mkdir(); err != nil {
		return errors.Trace(err)
	}
	return nil
}

func (d *M3u8Downloader) parse() (shards []string, err error) {
	Logger.Debugf("[STEP1] parse m3u8 file: %s", d.url)

	interval := 3 * time.Second
	err = d.retry(d.maxRetry, func() (stop bool, err error) {
		shards, err = d.parseM3u8Url(d.url, d.isShardFunc)
		if err == nil {
			return true, nil
		}
		errHandler(err)
		time.Sleep(interval)
		return false, nil
	})
	if err != nil {
		return nil, errors.Trace(err)
	}
	if d._encrypt {
		return nil, fmt.Errorf("unsupported encrypt m3u8 file")
	}
	return shards, nil
}

func (d *M3u8Downloader) fix(shards []string, m3u8Url string) map[int]string {
	Logger.Debug("[STEP2] fix shards url")

	res := make(map[int]string, len(shards))
	for idx, shardUrl := range shards {
		res[idx] = d.fixShardFunc(shardUrl, m3u8Url)
	}

	d._totalShard = len(shards)
	d._bar = NewBar(0, len(shards))
	return res
}

func (d *M3u8Downloader) download(shards map[int]string) error {
	Logger.Debugf("[STEP3] download [%d] shards", len(shards))

	d._bar.Start()
	err := d.retry(d.maxRetry, func() (stop bool, err error) {
		shards, err = d.filter(shards)
		if err != nil {
			return true, errors.Trace(err)
		}
		d._bar.Reset(d._totalShard - len(shards))
		d.downloadShards(shards, d.downPath)
		_done, err := d.done()
		if err != nil {
			return true, errors.Trace(err)
		}
		return _done, nil
	})
	return errors.Trace(err)
}

func (d *M3u8Downloader) merge() error {
	Logger.Debug("[STEP4] merge all shards")

	save, err := os.Create(filepath.Join(d.savePath, d.saveName))
	if err != nil {
		return errors.Trace(err)
	}
	defer save.Close()

	files, err := ioutil.ReadDir(d.downPath)
	if err != nil {
		return errors.Trace(err)
	}
	for _, f := range files {
		content, err := ioutil.ReadFile(filepath.Join(d.downPath, f.Name()))
		if err != nil {
			return errors.Trace(err)
		}
		if _, err := save.Write(content); err != nil {
			return errors.Trace(err)
		}
	}
	return nil
}

func (d *M3u8Downloader) clear() error {
	if d.clearDebris {
		Logger.Debug("[STEP5] clear debris")
		if err := os.RemoveAll(d.downPath); err != nil {
			return errors.Trace(err)
		}
	}
	return nil
}

// prepare -> parse -> fix -> download -> merge -> clear
func (d *M3u8Downloader) Run() (err error) {
	Logger.Infof("download: %s\n", d.saveName)

	if err = d.prepare(); err != nil {
		return errors.Trace(err)
	}
	shards, err := d.parse()
	if err != nil {
		return errors.Trace(err)
	}
	shardMap := d.fix(shards, d.url)
	if err = d.download(shardMap); err != nil {
		return errors.Trace(err)
	}
	if err = d.merge(); err != nil {
		return errors.Trace(err)
	}
	if err = d.clear(); err != nil {
		return errors.Trace(err)
	}
	Logger.Infof("fininsh: %s\n\n", d.saveName)
	return nil
}

func (d *M3u8Downloader) Crawl() {
	errHandler(d.Run())
}

func errHandler(err error) {
	if err != nil {
		Logger.Error(errors.ErrorStack(err))
	}
}

var (
	url     string
	name    string
	down    string
	save    string
	clear   bool
	threads uint
)

func main() {
	flag.StringVar(&url, "url", "", "url")
	flag.StringVar(&name, "name", "video.ts", "video name")
	flag.StringVar(&down, "down", "", "down path")
	flag.StringVar(&save, "save", "", "save path")
	flag.BoolVar(&clear, "clear", true, "clear debris")
	flag.UintVar(&threads, "threads", 16, "threads")
	flag.Parse()

	if len(url) == 0 {
		panic("url is null")
	}

	New(url, name, down, save, clear, threads, 5,
		nil, nil, nil).Crawl()
}
