# 音频 / 语音领域术语库

精读论文前先扫一遍这个文件，把领域基础知识装进上下文。包含术语词典、关键基线对照、常用评测指标。

---

## 1. 核心术语词典

### 1.1 信号表示

| 术语 | 全称 / 定义 | 典型出处 |
|---|---|---|
| **Waveform** | 原始波形（采样率 16k/24k/44.1k Hz） | 所有音频论文 |
| **Mel-Spectrogram** | 对数 Mel 频谱图（通常 80 或 100 维，10/12.5 ms hop） | FastSpeech, VITS |
| **STFT / iSTFT** | 短时傅里叶变换 / 逆变换 | 声码器、源分离 |
| **F0 / Pitch** | 基频，描述音高 | Prosody 控制、SVC |
| **Phoneme** | 音素（最小发音单位），常用 IPA / CMUDict | TTS 前端 |
| **Discrete Audio Token** | 把音频离散化成 token 序列，便于 LLM 处理 | VALL-E, AudioLM |
| **Semantic Token** | 通常来自 HuBERT/WavLM 的 SSL 特征做 k-means 聚类得到，承载语言内容 | AudioLM, SpeechGPT |
| **Acoustic Token** | 通常来自 Codec（EnCodec/SoundStream）的 RVQ 输出，承载声学细节 | AudioLM, VALL-E |

### 1.2 模型组件

| 术语 | 含义 | 备注 |
|---|---|---|
| **Codec** | 神经音频编解码器，把 waveform 压成离散码 | EnCodec, SoundStream, DAC |
| **RVQ (Residual VQ)** | 残差向量量化，多层码本逐层量化残差 | 几乎所有现代 codec 都用 |
| **Vocoder** | 声码器，Mel→Waveform | HiFi-GAN, BigVGAN, Vocos |
| **Duration Predictor** | 时长预测器，为每个 phoneme 预测帧数 | FastSpeech 系列 |
| **Forced Alignment** | 强制对齐，把文本和音频在时间上对上 | MFA, Wav2Vec-Aligner |
| **Length Regulator** | 按 duration 把 phoneme 序列扩展成帧序列 | FastSpeech |
| **Flow Matching / CFM** | Conditional Flow Matching，比 diffusion 更快的生成范式 | Voicebox, F5-TTS |
| **Speaker Encoder** | 提取说话人特征向量 | YourTTS, XTTS |
| **Prompt / Reference** | 零样本 TTS 中的参考音频（决定音色/风格） | VALL-E, NaturalSpeech 2/3 |

### 1.3 任务范式

| 术语 | 含义 |
|---|---|
| **AR TTS** | 自回归 TTS（Tacotron, VALL-E）；高质量但慢 |
| **NAR TTS** | 非自回归 TTS（FastSpeech, NaturalSpeech）；快但需 duration |
| **Zero-Shot / In-Context TTS** | 给一段参考音频，直接复刻音色，无需 fine-tune（VALL-E 范式） |
| **Streaming TTS / ASR** | 流式：边收边出，关键指标是首包延迟和 RTF |
| **Chunk-based** | 把音频切 chunk 处理，常用于流式 |
| **VAD** | Voice Activity Detection 语音活动检测 |
| **Turn-Taking** | 谁说话谁停的决策机制 |
| **Barge-In / Interruption** | 用户中途打断，模型要及时停止生成 |
| **Full-Duplex** | 同时听/说，区别于半双工（轮流） |
| **End-of-Speech (EOS)** | 用户话说完的判定 |
| **S2ST** | Speech-to-Speech Translation 语音到语音翻译 |
| **SVC** | Singing Voice Conversion 歌声转换 |

### 1.4 训练相关

| 术语 | 含义 |
|---|---|
| **Mel Loss / Reconstruction Loss** | 重建损失 |
| **Adversarial Loss** | GAN 判别器损失，常用于声码器 |
| **Mel-GAN / Multi-Period / Multi-Scale Discriminator** | HiFi-GAN 系判别器 |
| **Speech DPO / RLHF for TTS** | 用偏好数据微调 TTS（Speech-DPO, MOS-DPO） |
| **Classifier-Free Guidance (CFG)** | 扩散/Flow 中的引导技巧 |
| **Teacher Forcing** | AR 训练时用真实 token 做下一步输入 |

---

## 2. 关键基线模型速查表

> 写论文笔记时，**对比章节必须用具体模型名**，不要写"和现有 TTS 模型对比"这种空话。

### 2.1 TTS

| 模型 | 一句话定位 | 关键论文 |
|---|---|---|
| **Tacotron 2** | 早期 AR Mel→Vocoder 二阶段 | Shen 2018 |
| **FastSpeech 2** | NAR + duration predictor 经典 | Ren 2021 |
| **VITS** | 端到端 Flow + Adversarial | Kim 2021 |
| **NaturalSpeech 2/3** | 微软 latent diffusion / RVQ-DiT | Shen 2023/2024 |
| **VALL-E / VALL-E 2** | 把 TTS 当条件语言建模，离散 codec token | Wang 2023 |
| **Voicebox** | Meta 的 Flow Matching mask-and-infill | Le 2023 |
| **CosyVoice / CosyVoice 2** | 阿里，supervised semantic token + flow + vocoder | Du 2024 |
| **F5-TTS** | 上海交大，纯 Flow Matching、无 phoneme、无 duration | Chen 2024 |
| **Fish-Speech / Fish-Audio** | 开源社区，autoregressive token TTS | 2024 |
| **GPT-SoVITS** | 中文社区零样本 TTS 红人 | 2024 |
| **XTTS-v2** | Coqui，多语种零样本 | 2024 |
| **Spark-TTS** | 单一 LLM-based + BiCodec | 2025 |
| **Step-Audio** | 阶跃星辰开源 130B 多模态语音模型 | 2025 |

### 2.2 ASR

| 模型 | 一句话定位 |
|---|---|
| **Whisper / Whisper-Turbo** | OpenAI，强多语种、强鲁棒、长音频金标准 |
| **Conformer / Zipformer** | 端到端 ASR 主流 backbone（Zipformer 来自 k2/Icefall） |
| **Paraformer** | 阿里，非自回归 ASR |
| **SenseVoice** | 阿里，多任务（ASR+情感+事件） |
| **Distil-Whisper** | 蒸馏版 Whisper |
| **OWSM** | 开源对标 Whisper |

### 2.3 Codec / Tokenizer

| 模型 | 码率 | 备注 |
|---|---|---|
| **EnCodec** | 1.5-24 kbps | Meta, 8 层 RVQ |
| **SoundStream** | 3-18 kbps | Google |
| **DAC** | 0.5-8 kbps | Descript Audio Codec，重建质量 SOTA |
| **SpeechTokenizer** | 分语义/声学层级 | 复旦 |
| **Mimi** | 1.1 kbps，12.5 Hz | Kyutai Moshi 内部 codec，专为 LLM 设计 |
| **WavTokenizer** | 单码本，低码率 | 上交 2024 |
| **X-Codec / X-Codec 2** | 同时建模语义+声学的统一 codec | 2024-2025 |
| **BigCodec** | 大模型化 codec | 2024 |

### 2.4 Speech LLM / Audio LM

| 模型 | 定位 |
|---|---|
| **AudioLM** | Google，三段式 semantic→coarse→fine |
| **VALL-E** | TTS 当条件 LM，离散 token AR |
| **SpeechGPT** | 复旦，离散 token 多模态 LLM |
| **Qwen2-Audio / Qwen2.5-Omni** | 阿里，强 audio understanding |
| **GLM-4-Voice** | 智谱，端到端语音对话 |
| **MiniCPM-o** | OpenBMB 多模态 Omni |
| **Mini-Omni / Mini-Omni 2** | 清华，开源端到端语音对话 |
| **Moshi / Moshi-v2** | Kyutai，全双工、低延迟语音对话标杆 |
| **Step-Audio** | 阶跃星辰 |
| **LLaMA-Omni** | 中科院 |
| **Baichuan-Omni** | 百川 |

### 2.5 全双工 / 对话

| 模型 | 关键点 |
|---|---|
| **Moshi** | 全双工双流建模，160 ms 端到端延迟 |
| **dGSLM** | 离散 GSLM，双说话人对话 |
| **SyncLLM** | 实时双向 LLM |
| **VITA** | 腾讯多模态交互 |

### 2.6 SSL 表示

| 模型 | 输出 |
|---|---|
| **wav2vec 2.0** | 自监督连续特征 |
| **HuBERT** | masked prediction，常做 k-means 提语义 token |
| **WavLM** | 微软，强 speaker + content 兼顾 |
| **BEATs** | 通用音频理解 |
| **MERT** | 音乐表示 |
| **XEUS / S4 / Owsm-CTC** | 多语种语音表示 |

---

## 3. 常见评测指标

### 3.1 TTS 主观

| 指标 | 含义 | 典型数字 |
|---|---|---|
| **MOS** | Mean Opinion Score 主观自然度评分（1-5） | 强模型 4.3-4.6 |
| **CMOS** | Comparative MOS（A/B 相对偏好） | ±0.05 显著 |
| **UTMOS / UTMOSv2** | UTokyo 训的自动 MOS 预测 | 4.0+ 算强 |
| **DNSMOS** | 微软训的语音质量预测 | — |

### 3.2 TTS 客观

| 指标 | 含义 | 备注 |
|---|---|---|
| **WER / CER** | ASR 反解后的词/字错率（衡量可懂度） | Whisper ASR 算 |
| **SIM-O** | 与原 prompt 的说话人相似度（speaker embedding cos） | 0.6+ 算好 |
| **SIM-R** | 与重合成 ground truth 的相似度 | — |
| **SECS** | Speaker Encoder Cosine Similarity（同上别名） | — |
| **PESQ / STOI** | 信号质量、可懂度（更多用在增强） | — |
| **F0 RMSE / DUR RMSE** | 韵律相似度 | — |

### 3.3 ASR

| 指标 | 含义 |
|---|---|
| **WER** | Word Error Rate |
| **CER** | Character Error Rate（中文常用） |
| **MIX-Error** | 混合中英 WER |
| **Real-Time Factor (RTF)** | 处理 1 秒音频要几秒，<1 才能实时 |

### 3.4 全双工 / 对话延迟

| 指标 | 含义 |
|---|---|
| **First-Packet Latency** | 首包响应延迟（用户停说→模型发出第一帧） |
| **End-to-End Latency** | 端到端往返延迟 |
| **Barge-in Reaction Time** | 用户打断到模型停止生成的反应时间 |

### 3.5 Codec

| 指标 | 含义 |
|---|---|
| **bps / kbps** | 码率（越低越好，但要不损失质量） |
| **ViSQOL** | 客观质量分 |
| **STOI** | 可懂度 |
| **MUSHRA** | 主观多刺激评测 |

---

## 4. 常见数据集

| 数据集 | 规模 / 类型 |
|---|---|
| **LibriSpeech** | 1000h 英文有声书 ASR |
| **LibriTTS / LibriTTS-R** | 585h 英文 TTS（多说话人） |
| **GigaSpeech** | 10kh 多源英文 ASR |
| **Common Voice** | 多语种众包 ASR |
| **VCTK** | 110 说话人英文 TTS |
| **LJSpeech** | 单说话人英文 TTS |
| **AISHELL-1/2/3/4** | 中文 ASR/TTS |
| **WenetSpeech / KeSpeech** | 万小时中文 ASR |
| **Emilia / Emilia-Yodas** | 多语种 100kh+ TTS 训练集 |
| **Seed-TTS-eval** | TTS zero-shot 评测集（en/zh） |
| **MLS** | Multilingual LibriSpeech |
| **SLR / OpenSLR** | 一系列开源数据集编号 |

---

## 5. 阅读 checkpoints（精读时务必核对）

- [ ] 音频表示是 waveform / Mel / discrete token 中的哪种？码率/帧率多少？
- [ ] 是 AR 还是 NAR？如果是 NAR，时长怎么来的？
- [ ] 训练数据是哪些公开集？规模？是否清洗？
- [ ] 评测用了 LibriTTS / Seed-TTS-eval / SeedTTS / 自建 test set？
- [ ] WER 用什么 ASR 算的？（Whisper-large-v3 / -turbo / Paraformer）
- [ ] SIM 用什么 speaker encoder 算的？（WavLM-TDNN / ECAPA / Resemblyzer）
- [ ] 与 VALL-E / Voicebox / CosyVoice / F5-TTS 等强基线是否有对比？
- [ ] 推理延迟、RTF 是否报告？是否流式？
- [ ] 是否开源代码、checkpoint、训练数据？
