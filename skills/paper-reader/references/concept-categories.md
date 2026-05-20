# 概念自动归类规则（音频/语音方向）

概念库位置：`{CONCEPTS_PATH}`

先用 `ls {CONCEPTS_PATH}` 查看已有子目录，再按下表分类。**只有方法/模型/数据集/技术概念才进概念库**，论文标题、人名、机构名一律不要建概念。

| 子目录 | 归类标准 | 示例 |
|--------|----------|------|
| `1-TTS与语音合成` | 端到端 TTS、零样本、表达性、流式 TTS、风格控制、个性化 | FastSpeech, VITS, NaturalSpeech, VALL-E, Voicebox, CosyVoice, F5-TTS, Fish-Speech, GPT-SoVITS, ICL TTS |
| `2-ASR与语音识别` | 端到端 ASR、流式 ASR、CTC/Transducer、长音频识别、多语种 ASR | Whisper, Conformer, Zipformer, RNN-T, CTC, Streaming ASR, Long-form ASR |
| `3-Audio-Codec与Tokenizer` | 神经音频编码器、离散音频 token、码本设计、RVQ | EnCodec, SoundStream, DAC, SpeechTokenizer, Mimi, WavTokenizer, Single-Codebook, RVQ |
| `4-Vocoder与声码器` | Mel→波形的声码器、神经声码器 | HiFi-GAN, BigVGAN, Vocos, WaveNet, DiffWave, UnivNet, iSTFT-Net |
| `5-Speech-LLM与AudioLM` | 语音/音频大模型、speech-in/speech-out、对话能力 | VALL-E, AudioLM, SpeechGPT, Qwen2-Audio, GLM-4-Voice, SALMONN, Audio Flamingo |
| `6-全双工与对话` | duplex、turn-taking、barge-in、reaction latency、spoken dialogue | Moshi, dGSLM, FullDuplex, Turn-taking, Barge-in, VAD-Free Duplex |
| `7-Omni与多模态` | speech-vision-text 统一模型、any-to-any 多模态 | GPT-4o, Mini-Omni, MiniCPM-o, Lyra, Baichuan-Omni, NExT-GPT |
| `8-Diffusion与FlowMatching` | 用在 TTS/Audio 上的扩散/Flow Matching/CFM | DDPM, DPM-Solver, Flow Matching, CFM, Rectified Flow, EDM, NFE |
| `9-语音SSL与表示` | 自监督语音预训练、声学表示学习 | HuBERT, WavLM, wav2vec 2.0, data2vec, BEATs, MERT, XEUS |
| `10-语音翻译与跨语言` | S2ST、跨语言 TTS、code-switch、多语种 | SeamlessM4T, Translatotron, AudioPaLM, XPhoneBERT, Multilingual TTS |
| `11-韵律与情感` | prosody、情感、风格、表达力、副语言 | Prosody Encoder, Style Token, GST, Emotion Embedding, Paralinguistic |
| `12-数据集与评测` | 数据集、评测集、benchmark、评测指标 | LibriSpeech, LibriTTS, GigaSpeech, Common Voice, Emilia, WenetSpeech, MOS, UTMOS, WER, CER, SECS, SIM-O |
| `13-训练方法与对齐` | 时长建模、强制对齐、DPO/RLHF for speech、训练范式 | Duration Predictor, Forced Alignment, MFA, Speech DPO, Distillation, Curriculum |
| `14-LLM基础` | 通用 LLM 方法（仅在论文涉及时建） | Transformer, MoE, RoPE, FlashAttention, KV Cache, Speculative Decoding, GRPO, DPO |
| `15-其他音频任务` | 增强、分离、检测、关键词检索、SVC、声音事件 | Speech Enhancement, Source Separation, KWS, Voice Conversion, Sound Event Detection |
| `0-待分类` | **仅在完全无法判断时**才用，应尽量避免 | — |

## 判断顺序

1. 看概念是否是**具体方法/模型**（如 `EnCodec`、`HiFi-GAN`）→ 进对应子目录
2. 看是否是**通用技术组件**（如 `RVQ`、`Duration Predictor`、`Forced Alignment`）→ 进对应方向子目录
3. 看是否是**数据集/评测指标**（如 `LibriTTS`、`UTMOS`）→ `12-数据集与评测`
4. 跨方向概念（如 `Flow Matching` 既用于 TTS 也用于通用生成）→ 选**主要应用场景**所在子目录；本仓库默认 `Flow Matching` 放 `8-Diffusion与FlowMatching`
5. 完全不沾边的通用 LLM 方法（如 `RoPE`）→ `14-LLM基础`

## 概念笔记模板

```markdown
---
type: concept
aliases: [中文别名, 英文别名]
---

# 概念名称

## 定义
{一句话定义。对于音频领域，必要时说明：处理的是 waveform / Mel / discrete token 中的哪种}

## 数学形式
$$公式$$

（如适用，写清楚：输入维度、输出维度、采样率/帧率/token 率）

## 核心要点
1. ...
2. ...

## 代表工作
- [[Paper1]]: ...
- [[Paper2]]: ...

## 评测/常见数字
{该方法在常见 benchmark 上的典型数字。例如 codec 的码率、TTS 的 MOS/SECS、ASR 的 WER}

## 相关概念
- [[相关概念1]]
- [[相关概念2]]
```
