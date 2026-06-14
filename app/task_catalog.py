from __future__ import annotations

from app.models import AppEdition, CompetitionDefinition, TaskDefinition

STANDARD_OUTPUTS = [
    "README.md",
    "train.py",
    "predict.py",
    "run.py",
    "run_on_unihiker.py",
    "setup_unihiker.sh",
    "deploy.sh",
    "deploy.bat",
    "notebook.ipynb",
    "ai_runtime/__init__.py",
    "ai_runtime/core.py",
    "hardware/README.md",
    "requirements.txt",
    "submission/README.md",
    "docs/competition_checklist.md",
    "docs/ai_validation.md",
    "speech/README.md",
    "speech/speech_output.py",
    "speech/voice_config.json",
    "creative_examples/01_display_result.py",
    "creative_examples/02_trigger_buzzer.py",
    "creative_examples/03_count_and_log.py",
    "creative_examples/04_servo_control.py",
]


SMART_MUSEUM_TASKS = [
    TaskDefinition(
        slug="heritage_face_intro",
        title="挑战一：认识非遗传承匠人",
        summary="为人脸卡片识别和人物介绍播报生成程序骨架。",
        student_goal="生成符合“这是XXX，XXX”格式的识别结果展示和播报模板。",
        group="小学/初中/高中",
        requirement_source="附件5 智能博物 常规挑战一",
        competition_requirements=[
            "识别任务一卡片触发挑战",
            "实时拍照识别人脸卡片",
            "使用人脸识别AI技能",
            "小学播报：这是XXX",
            "初中/高中播报：这是XXX，XXX",
        ],
        ai_capability="image_classifier",
        sample_dataset_kind="image",
        runtime_requirements=["scikit-learn", "joblib", "numpy", "pillow", "onnxruntime"],
        voice_profile="dfrobot_tts_broadcast",
        paused_features=["摄像头实时拍照"],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "添加人物类别并上传卡片照片",
            "点击训练查看准确率",
            "上传新卡片照片测试",
            "导出挑战一材料包",
            "按硬件说明迁移到行空板",
        ],
    ),
    TaskDefinition(
        slug="heritage_ocr_typo",
        title="挑战二：了解非遗专业知识",
        summary="为知识卡片文字识别、错别字定位和更正播报生成程序骨架。",
        student_goal="生成可改造的 OCR 结果校验和错别字播报模板。",
        group="小学/初中/高中",
        requirement_source="附件5 智能博物 常规挑战二",
        competition_requirements=[
            "识别任务二卡片触发挑战",
            "实时拍照识别知识卡片文字",
            "小学定位1个错别字",
            "初中/高中定位2个错别字",
            "按规定格式显示并播报更正结果",
        ],
        ai_capability="ocr_typo_checker",
        sample_dataset_kind="ocr",
        runtime_requirements=["easyocr", "torch", "opencv-python-headless"],
        voice_profile="dfrobot_tts_broadcast",
        paused_features=[],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "输入正确的知识卡片文字",
            "保存正确文字",
            "输入带错字的文字测试",
            "导出挑战二材料包",
            "按硬件说明迁移到行空板",
        ],
    ),
    TaskDefinition(
        slug="heritage_text_classifier",
        title="挑战三：非遗文化分类学览",
        summary="把少量非遗词语或说明文本整理成可运行的分类示例。",
        student_goal="训练一个判断词语属于哪类非遗的文本分类模型，输出格式：XXX属于XXX。",
        group="小学/初中/高中",
        requirement_source="附件5 智能博物 常规挑战三",
        competition_requirements=[
            "实时拍照识别词语卡片",
            "训练并调用自建文本分类模型",
            "展示与播报格式：XXX属于XXX",
            "展示环节识别现场抽取的3-6张词语卡片",
            "全部挑战任务结束后播报提示语：挑战完成",
        ],
        ai_capability="text_classifier",
        sample_dataset_kind="text",
        runtime_requirements=["scikit-learn", "joblib", "numpy"],
        voice_profile="dfrobot_tts_broadcast",
        paused_features=[],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "添加非遗类别并粘贴词语例句",
            "点击训练查看准确率",
            "输入新词语测试",
            "导出挑战三材料包",
            "按硬件说明迁移到行空板",
        ],
    ),
    TaskDefinition(
        slug="heritage_sentence_classifier",
        title="挑战四：非遗文化深化认知",
        summary="为句子卡片识别、非遗类别和名称判断生成文本分类模板。",
        student_goal="生成符合“这是非遗XXX类别的XXX”格式的分类脚本。",
        group="小学/初中/高中",
        requirement_source="附件5 智能博物 常规挑战四",
        competition_requirements=[
            "识别任务四卡片触发挑战",
            "实时识别句子卡片",
            "训练并调用自建文本分类模型",
            "识别3-6张现场抽取句子卡片",
            "播报格式：这是非遗XXX类别的XXX",
            "全部挑战任务结束后播报提示语：挑战完成",
        ],
        ai_capability="text_classifier",
        sample_dataset_kind="text",
        runtime_requirements=["scikit-learn", "joblib", "numpy"],
        voice_profile="dfrobot_tts_broadcast",
        paused_features=[],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "添加类别并粘贴句子例句",
            "点击训练查看准确率",
            "输入新句子测试",
            "导出挑战四材料包",
            "按硬件说明迁移到行空板",
        ],
    ),
    TaskDefinition(
        slug="heritage_qa_helper",
        title="非遗知识问答模板",
        summary="把竞赛知识材料整理成固定问答程序模板。",
        student_goal="训练一个能根据问题找到最相关答案的检索式问答助手。",
        group="创意拓展",
        requirement_source="附件5 智能博物 创意拓展",
        competition_requirements=[
            "围绕非遗传承与宣传主题",
            "不得和常规挑战一至四重复",
            "突出图像识别、语音识别、自然语言处理等人工智能技术",
            "提交创作说明、程序代码、作品照片和2分钟内演示视频",
        ],
        ai_capability="qa_retrieval",
        sample_dataset_kind="qa",
        runtime_requirements=["scikit-learn", "joblib", "numpy"],
        voice_profile="dfrobot_tts_broadcast",
        paused_features=["语音识别"],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "每行录入一组问答",
            "点击训练建立问答索引",
            "输入新问题测试",
            "导出创意拓展材料包",
            "补充作品照片和说明",
        ],
    ),
]

FUTURE_CREATOR_TASKS = [
    TaskDefinition(
        slug="image_recognition_starter",
        title="图像识别快速模板",
        summary="生成一个适合学生改造的图像识别项目骨架。",
        student_goal="生成可在电脑或边缘设备上继续修改的图像识别脚本和说明。",
        group="小学/初中/高中",
        requirement_source="附件4 优创未来 图像识别规定技术要求",
        competition_requirements=[
            "现场发布4类卡片",
            "小学自选1类完成识别",
            "初中/高中自选2类完成识别",
            "展示环节由专家指定一种识别",
        ],
        ai_capability="image_classifier",
        sample_dataset_kind="image",
        runtime_requirements=["scikit-learn", "joblib", "numpy", "pillow", "onnxruntime"],
        voice_profile="none",
        paused_features=[],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "添加卡片类别并上传图片",
            "点击训练查看准确率",
            "上传新图片测试",
            "导出比赛材料包",
            "按硬件说明迁移到行空板",
        ],
    ),
    TaskDefinition(
        slug="sensor_decision_template",
        title="传感器决策程序模板",
        summary="生成一个读取输入、判断状态、输出动作的硬件控制程序骨架。",
        student_goal="生成适合接入行空板 M10 与 DFRobot 传感器/执行器外设的决策逻辑示例。",
        group="创意应用",
        requirement_source="附件4 优创未来 具身智能与智慧医疗",
        competition_requirements=[
            "围绕具身智能、智慧医疗设计创意应用",
            "完成方案设计、硬件搭建、程序编写和软件调试",
            "体现认知、推理、决策等类人智能功能",
            "提交创作说明、演示视频和实物照片",
        ],
        ai_capability="sensor_decision_model",
        sample_dataset_kind="sensor",
        runtime_requirements=["scikit-learn", "joblib", "numpy"],
        voice_profile="none",
        paused_features=["真实传感器连接", "真实执行器控制"],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "设计输入信号和动作",
            "粘贴传感器CSV数据",
            "点击训练并查看决策规则",
            "输入新数值测试",
            "导出比赛材料包",
        ],
    ),
    TaskDefinition(
        slug="primary_voice_image_interaction",
        title="小学组：语音互动与单类图像识别",
        summary="为关键词语音互动和1类卡片识别生成轻量模板。",
        student_goal="生成小学组规定技术要求的程序与材料清单。",
        group="小学组",
        requirement_source="附件4 优创未来 小学组规定技术要求",
        competition_requirements=[
            "基于关键词识别的人机语音互动1条",
            "具体关键词现场发布",
            "4类卡片中自选1类完成识别",
            "可包含语音合成、语音交互控制、运动控制",
        ],
        ai_capability="image_classifier",
        sample_dataset_kind="image",
        runtime_requirements=["scikit-learn", "joblib", "numpy", "pillow", "onnxruntime"],
        voice_profile="unihiker_keyword_voice",
        paused_features=[],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "选择1类卡片并上传图片",
            "点击训练查看准确率",
            "上传新图片测试",
            "导出材料包并配置现场关键词",
            "按硬件说明迁移到行空板",
        ],
    ),
    TaskDefinition(
        slug="junior_model_calling_workflow",
        title="初中组：视觉模型训练与调用",
        summary="为关键词语音互动、2类卡片识别和模型调用生成项目骨架。",
        student_goal="生成初中组模型训练、调用和硬件迁移材料。",
        group="初中组",
        requirement_source="附件4 优创未来 初中组规定技术要求",
        competition_requirements=[
            "基于关键词识别的人机语音互动1条",
            "4类卡片中自选2类完成识别",
            "体现视觉模型训练和模型调用",
            "可结合自然语言处理和运动控制",
        ],
        ai_capability="image_classifier",
        sample_dataset_kind="image",
        runtime_requirements=["scikit-learn", "joblib", "numpy", "pillow", "onnxruntime"],
        voice_profile="unihiker_keyword_voice",
        paused_features=[],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "添加2类卡片并上传图片",
            "点击训练查看准确率",
            "上传新图片测试",
            "导出材料包并配置现场关键词",
            "按硬件说明迁移到行空板",
        ],
    ),
    TaskDefinition(
        slug="senior_llm_vision_motion",
        title="高中组：大模型语音互动、视觉识别与运动控制",
        summary="为行空板 M10 + DFRobot 外设路线生成高中组视觉识别、语音接口和运动控制方案骨架。",
        student_goal="生成高中组完整技术链路的程序模板和验收清单。",
        group="高中组（含中职）",
        requirement_source="附件4 优创未来 高中组规定技术要求",
        competition_requirements=[
            "基于人工智能大模型的人机语音互动",
            "大模型智能体角色设定须与现场任务主题相符",
            "4类卡片中自选2类完成识别",
            "使用机械装置自主夹取3个轻质立方体并摆放",
        ],
        ai_capability="image_classifier",
        sample_dataset_kind="image",
        runtime_requirements=["scikit-learn", "joblib", "numpy", "pillow", "onnxruntime"],
        voice_profile="unihiker_keyword_voice",
        paused_features=["真实大模型智能体", "真实机械装置控制", "行空板M10本地大模型需外接服务或后续扩展"],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "添加2类卡片并上传图片",
            "点击训练查看准确率",
            "上传新图片测试",
            "导出比赛材料包",
            "按说明接入语音和运动控制",
        ],
    ),
]

GENERAL_TASKS = [
    TaskDefinition(
        slug="general_image_classifier",
        title="图像分类",
        summary="上传几类图片，训练一个能认出新图片属于哪一类的模型。",
        student_goal="理解图像分类的完整流程：采集数据、训练、测试、导出。",
        group="通用练习",
        requirement_source="机器学习基础练习",
        competition_requirements=[
            "准备至少2个类别的图片，每类2张以上",
            "训练后查看准确率",
            "用一张新图片测试模型",
            "导出材料包并在电脑上运行验证",
        ],
        ai_capability="image_classifier",
        sample_dataset_kind="image",
        runtime_requirements=["scikit-learn", "joblib", "numpy", "pillow", "onnxruntime"],
        voice_profile="none",
        paused_features=[],
        suggested_hardware=["student_laptop"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "添加图片类别",
            "每类上传几张图片",
            "点击训练",
            "上传新图片测试",
            "导出材料包",
        ],
        concept_intro=(
            "图像分类是让计算机通过看大量图片「学会」区分不同类别的技术。"
            "就像你看了很多苹果和香蕉的照片，就能认出新照片里是哪种水果——"
            "计算机也通过同样的方式提取视觉特征、建立判断规则。"
            "图片数量和多样性决定了模型的泛化能力：只靠少量相似图片训练的模型，"
            "遇到角度或光线稍有不同的图片就容易出错，这种现象叫「过拟合」。"
        ),
        step_guides=[
            # 准备数据
            "每个类别准备至少 5 张有代表性的图片，角度、光线和背景越多样越好。"
            "避免同一张图复制多份——重复图片不会让模型学到新东西，反而浪费配额。"
            "如果没有自己的图片，可以点击「加载样本数据包」体验预置数据集。",
            # 训练模型
            "训练时模型会提取每张图片的视觉特征（颜色分布、纹理、形状），"
            "再学习哪些特征组合对应哪个类别。"
            "报告里的「交叉验证准确率」反映的是模型对没见过的图片的判断能力，"
            "比训练准确率更可信——训练准确率高但交叉验证低，说明模型在死记训练图。",
            # 测试效果
            "上传一张没有参与过训练的图片，模型会给出预测类别和置信度（0–100%）。"
            "置信度越高说明模型越「有把握」。"
            "如果预测错误或置信度很低，通常需要回第 1 步补充更多有代表性的训练图片——"
            "尤其是和测试图片风格相似的样本。",
            # 导出材料
            "导出包含可运行的 predict.py 和训练好的模型文件（.joblib）。"
            "在自己的电脑上运行 python predict.py 可以验证模型是否正常工作，"
            "确认模型能独立运行，是一个项目真正完成的标志。导出前请确保已完成训练。",
        ],
        real_world_examples=[
            "手机相册自动把照片分成「人物 / 风景 / 美食」——背后就是图像分类。",
            "刷脸解锁、刷脸支付，先要认出「这是不是同一个人」。",
            "垃圾分类机器人对着传送带上的垃圾判断该投哪个桶。",
            "医生用 AI 辅助看 X 光片，初步判断哪些片子需要重点关注。",
        ],
        common_mistakes=[
            "每个类别只放几张几乎一样的图。同一物体多换角度、光线、背景才有用，"
            "复制粘贴同一张图不会让模型学到新东西。",
            "背景太固定——比如猫都拍在沙发上、狗都拍在草地上。"
            "这样模型可能学的其实是「沙发」和「草地」，一换背景就认错。",
        ],
        hands_on_experiments=[
            "加数据实验：先每类 3 张训练，记下准确率；再补到每类 10 张重新训练，"
            "对比准确率怎么变——亲眼看到「数据量决定上限」。",
            "特征对比：同一份数据分别用「像素」和「MobileNet 迁移学习」各训练一次，"
            "比较两次准确率，体会借用大网络提取特征有多管用（需先下载 MobileNet）。",
            "制造过拟合：故意每类只用 2 张图训练，观察训练准确率很高、"
            "交叉验证却很低——这就是「死记硬背」的样子。",
        ],
        next_steps=(
            "你已经会训练图像分类模型了。想知道手机是怎么「看懂」一张图的吗？"
            "去「深度学习地图」看看卷积神经网络（CNN）和 MobileNet 是怎么提取图像特征的。"
        ),
    ),
    TaskDefinition(
        slug="general_text_classifier",
        title="文本分类",
        summary="给几类文字示例，训练一个能判断新句子属于哪一类的模型。",
        student_goal="理解文本分类的完整流程：整理语料、训练、测试、导出。",
        group="通用练习",
        requirement_source="机器学习基础练习",
        competition_requirements=[
            "准备至少2个类别的文本，每类3条以上",
            "训练后查看准确率",
            "输入一条新文本测试模型",
            "导出材料包并在电脑上运行验证",
        ],
        ai_capability="text_classifier",
        sample_dataset_kind="text",
        runtime_requirements=["scikit-learn", "joblib", "numpy"],
        voice_profile="none",
        paused_features=[],
        suggested_hardware=["student_laptop"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "添加文本类别",
            "每类粘贴几条例句",
            "点击训练",
            "输入新句子测试",
            "导出材料包",
        ],
        concept_intro=(
            "文本分类让计算机根据文字内容把句子归类，比如判断一条评论是正面还是负面，"
            "或者识别一段话属于哪个主题。"
            "计算机并不真正「理解」文字的含义，而是通过统计哪些词在哪些类别中更常出现来做判断——"
            "这种方法叫 TF-IDF（词频-逆文档频率），简单却在很多场景下效果很好。"
        ),
        step_guides=[
            # 准备数据
            "每类至少准备 5 条有代表性的例句，句子风格越接近真实使用场景越好。"
            "不同类别的例句内容要有明显区别——如果两类文字「说的是同一类事」，"
            "模型会很难分辨。例如分类「运动」和「娱乐」时，"
            "避免把比赛报道同时放进两个类别。",
            # 训练模型
            "模型先把文字拆成词，统计词频，再找出哪些词在哪些类别中更常出现，形成分类依据。"
            "可选朴素贝叶斯、逻辑回归等多种算法，不确定选哪个可以点「对比所有模型」用同一份数据比较。"
            "交叉验证准确率低于 70% 通常说明数据太少或例句不够典型——回第 1 步补充。",
            # 测试效果
            "输入一条没出现过的句子，模型会预测它属于哪一类并给出置信度。"
            "如果预测错误，想想这句话里有没有典型词汇；"
            "然后回第 1 步补充包含这类词汇的例句，再重新训练。",
            # 导出材料
            "导出的 predict.py 接受命令行参数：python predict.py \"你的文字\" "
            "会输出预测类别和置信度，可以直接集成到你自己的程序中。"
            "导出包里也附带完整的词汇表和模型文件，无需网络即可运行。",
        ],
        real_world_examples=[
            "邮箱自动把垃圾邮件拦进垃圾箱——最早成名的文本分类应用。",
            "电商把商品评论分成「好评 / 差评」，帮商家快速看口碑。",
            "新闻 App 给每篇文章自动打上「体育 / 财经 / 娱乐」主题标签。",
            "客服系统读懂用户留言，自动转给对应的部门处理。",
        ],
        common_mistakes=[
            "两个类别其实「说的是同一类事」，模型分不开。"
            "比如同时分「足球新闻」和「体育新闻」，内容高度重叠，注定混淆。",
            "例句太短、太套路化，每条几乎一样，模型学不到真正有区分度的词。"
            "多收集一些自然、真实的句子效果更好。",
        ],
        hands_on_experiments=[
            "算法赛跑：点「对比所有模型」，看朴素贝叶斯、逻辑回归在你这份数据上"
            "谁更准、谁更快——不同算法适合不同数据。",
            "加数据实验：每类例句从 3 条加到 10 条，观察交叉验证准确率的变化。",
            "找混淆：训练后看「混淆矩阵」，哪两类最容易被搞混？"
            "回第 1 步给它们补一些更有区分度的例句，再训练一次。",
        ],
        next_steps=(
            "平台用的是 TF-IDF 词频统计——只数词、不懂语义。"
            "真正能「理解」一句话含义的大模型（如 BERT）是怎么做到的？"
            "去「深度学习地图」第 4 节看文本技术从词袋到 Transformer 的演进。"
        ),
    ),
    TaskDefinition(
        slug="general_audio_classifier",
        title="语音分类",
        summary="给几类声音录音，训练一个能听出新声音属于哪一类的模型。",
        student_goal="理解声音分类的完整流程：录音、提取特征、训练、测试、导出。",
        group="通用练习",
        requirement_source="机器学习基础练习",
        competition_requirements=[
            "准备至少2个类别的声音，每类2段以上",
            "用页面录音按钮录制，或上传 WAV 文件",
            "训练后录一段新声音测试",
            "导出材料包并在电脑上运行验证",
        ],
        ai_capability="audio_classifier",
        sample_dataset_kind="audio",
        runtime_requirements=["scikit-learn", "joblib", "numpy"],
        voice_profile="none",
        paused_features=[],
        suggested_hardware=["student_laptop"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "添加声音类别",
            "每类录几段声音",
            "点击训练",
            "录新声音测试",
            "导出材料包",
        ],
        concept_intro=(
            "声音分类让计算机通过分析声波的特征区分不同类型的声音。"
            "与识别语言文字不同，这里的模型判断的是声音的音调、节奏和音量等物理特征，"
            "不需要听懂「说的是什么」。"
            "系统把每段录音分解成频率片段，提取数值特征，再用这些数字训练分类模型——"
            "整个过程只分析声波形状，因此对语言和方言没有依赖。"
        ),
        step_guides=[
            # 准备数据
            "每段录音保持 1–3 秒，声音要清晰、有代表性。"
            "录音环境越安静越好，背景噪音会混淆模型的判断。"
            "每类录 5 段以上，声音有自然变化（大声/小声、快/慢）效果更好。"
            "支持直接录制或上传 WAV 文件，也可以点「加载样本包」快速体验。",
            # 训练模型
            "系统把每段音频分解成频率片段，提取响度、音调分布（梅尔频带能量）等数值特征，"
            "再用这些数字训练分类模型——整个过程不处理文字，只分析声波形状。"
            "报告里的准确率反映的是模型对新录音的判断能力；"
            "数据量不足时交叉验证会跳过，这时增加录音数量最有帮助。",
            # 测试效果
            "录制一段新的声音，模型会判断它属于哪一类。"
            "如果识别不准，先检查两类声音是否足够「不像」——"
            "若两类声音太相似（比如同一个人的不同语调），模型也无法区分。"
            "此时建议让声音特征更有对比度，或补充更多不同场景的录音。",
            # 导出材料
            "导出的 predict.py 需要 sounddevice 库做实时录音。"
            "在行空板等嵌入式设备上运行时，使用 run.py 脚本——"
            "它已适配硬件麦克风接口，读取到声音后会自动调用模型并输出结果。",
        ],
        real_world_examples=[
            "智能音箱时刻听着唤醒词（「小爱同学」），听到才被叫醒。",
            "手机语音助手把你说的指令分成「打电话 / 放音乐 / 查天气」。",
            "工厂用麦克风听机器运转的声音，异响出现就预警可能要坏了。",
            "观鸟 App 听一段鸟叫，就能告诉你这是什么鸟。",
        ],
        common_mistakes=[
            "录音环境太吵，背景噪音盖过了真正要区分的声音，模型被噪音带偏。",
            "两类声音本质太像——比如同一个人用相近语调说不同的话，"
            "靠音色和节奏分不开。让两类声音的特征差别更明显些。",
        ],
        hands_on_experiments=[
            "加数据实验：每类录音从 2 段加到 8 段，看准确率怎么变。",
            "噪音实验：故意在很吵的环境录一类声音，和安静环境录的对比，"
            "亲身感受「数据质量」对结果的影响。",
            "找混淆：训练后看「混淆矩阵」，哪两类声音最容易被听混？",
        ],
        next_steps=(
            "平台用的是手工提取的声音特征（响度、音调分布）。"
            "更强的深度方案会把声音先变成一张「频谱图」，再当成图片用 CNN 识别——"
            "去「深度学习地图」第 5 节了解音频是怎么变成图片的。"
        ),
    ),
    TaskDefinition(
        slug="general_qa_retrieval",
        title="智能问答",
        summary="录入问答对，做一个能根据问题找到最相关答案的小助手。",
        student_goal="理解检索式问答的原理：相似度匹配和置信度。",
        group="通用练习",
        requirement_source="机器学习基础练习",
        competition_requirements=[
            "录入至少3组问答对",
            "训练后用新问题测试",
            "观察相似度分数和兜底回答",
            "导出材料包并在电脑上运行验证",
        ],
        ai_capability="qa_retrieval",
        sample_dataset_kind="qa",
        runtime_requirements=["scikit-learn", "joblib", "numpy"],
        voice_profile="none",
        paused_features=[],
        suggested_hardware=["student_laptop"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "整理问答知识点",
            "每行录入一组问答",
            "点击训练",
            "输入新问题测试",
            "导出材料包",
        ],
        concept_intro=(
            "检索式问答不是让 AI 自己编答案，而是从你提供的知识库中找出最匹配的已知问题，"
            "返回对应的答案。这种方法可靠、可控——AI 只会回答你教给它的内容，不会乱答。"
            "核心算法是 TF-IDF 向量相似度：把每个问题转换为数字向量，"
            "新问题进来时计算它和所有已知问题的相似度，返回得分最高的答案。"
        ),
        step_guides=[
            # 准备数据
            "每行一组，格式：问题 | 答案（竖线分隔）。"
            "同一个答案可以对应多种问法，比如「开始时间是？」「几点开始？」「什么时候开幕？」"
            "都指向同一个答案——这样问答更自然。"
            "知识点越多、问法越丰富，助手越实用。",
            # 训练模型
            "训练时系统会对每个问题做向量化，建立相似度检索索引。"
            "当新问题进来时，计算它和所有已知问题的相似度，返回最高分的答案。"
            "这叫检索式问答，不需要大型语言模型，在普通电脑上毫秒级完成，"
            "而且答案完全来自你输入的知识库，不会凭空捏造。",
            # 测试效果
            "输入一个没录入过的问题。结果会显示相似度分数（0–1）：分数越高匹配越好。"
            "低于阈值时系统会给出兜底回答，避免错误答案误导用户。"
            "如果一个问题总是找不到合适答案，回第 1 步补充对应的问答对。",
            # 导出材料
            "导出的 predict.py 读取命令行输入的问题，输出最匹配的答案和相似度分数。"
            "你可以把它集成到微信机器人、校园服务台等场景中——"
            "替换知识库文件即可更新问答内容，无需重新写代码。",
        ],
        real_world_examples=[
            "校园服务台的问答机器人，回答「图书馆几点关门」这类常见问题。",
            "电商客服自动回复「怎么退货」「运费多少」等高频问题。",
            "企业内部知识库：员工一搜，就找到最相关的制度条款。",
            "博物馆导览机：游客问「这件文物多少年了」，它从讲解词里找答案。",
        ],
        common_mistakes=[
            "一个答案只配了一种问法，换个说法就找不到。"
            "同一个答案要配多种问法（「几点开门」「什么时候营业」「开门时间」）。",
            "知识库太小，遇到没收录的问题只能给兜底回答。知识点越全，助手越好用。",
        ],
        hands_on_experiments=[
            "问法实验：先给一个答案只配 1 种问法，换个说法测试能不能命中；"
            "再补到 3 种问法重测——体会「问法多样性」的作用。",
            "阈值观察：故意输入一个知识库里完全没有的问题，"
            "看相似度分数有多低、是否触发了兜底回答。",
        ],
        next_steps=(
            "检索式问答是从你写好的知识库里「找」答案，可靠可控、不会乱编。"
            "生成式问答（像 ChatGPT 那样「现写」答案）和它有什么不同，各自又适合什么场景？"
            "新手教程第 3 章和术语表里有对比讲解。"
        ),
    ),
    TaskDefinition(
        slug="general_sensor_decision",
        title="传感器决策",
        summary="粘贴传感器数据表格，训练一个根据数值判断动作的决策树。",
        student_goal="理解决策树：模型如何从数据中学出 if-else 规则。",
        group="通用练习",
        requirement_source="机器学习基础练习",
        competition_requirements=[
            "准备带表头的CSV数据，最后一列是动作",
            "每种动作至少2行数据",
            "训练后查看决策规则",
            "输入一行新数值测试模型",
        ],
        ai_capability="sensor_decision_model",
        sample_dataset_kind="sensor",
        runtime_requirements=["scikit-learn", "joblib", "numpy"],
        voice_profile="none",
        paused_features=[],
        suggested_hardware=["student_laptop"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "设计输入信号和动作",
            "粘贴CSV数据",
            "点击训练并查看规则",
            "输入新数值测试",
            "导出材料包",
        ],
        concept_intro=(
            "传感器决策树让计算机根据传感器的数值（温度、光照、距离等）判断应该执行什么动作，"
            "就像一张数字版的 if-else 判断流程图。"
            "决策树的核心优点是结果可以直接读懂：训练完成后，"
            "你可以看到模型学出来的规则，比如「温度 > 28 且湿度 > 70 → 开风扇」，"
            "而不是像神经网络那样的黑箱。"
        ),
        step_guides=[
            # 准备数据
            "数据格式：带表头的 CSV，最后一列是动作标签，前面各列是传感器数值。"
            "每个传感器列的数值范围要覆盖真实使用场景，不要只提供极端值。"
            "每种动作至少准备 5 行样本，否则模型对该动作的判断会不可靠。"
            "可以粘贴 Excel 导出的 CSV 或手动输入。",
            # 训练模型
            "决策树通过找「最佳分叉点」学习规则，例如「温度 > 28 且湿度 > 70 → 开风扇」。"
            "训练后报告中可以看到学出来的规则树——规则简单易读是决策树最大的优点。"
            "如果规则看起来太复杂（很多层嵌套），通常说明数据中有噪声，"
            "可以尝试增加每种动作的样本数量。",
            # 测试效果
            "输入一组传感器数值，模型会预测应该执行哪个动作。"
            "尝试用接近分界线的数值（比如刚好在阈值上下）测试，"
            "观察模型是否做出合理判断。"
            "如果边界附近预测不稳定，通常需要补充更多该区间附近的训练样本。",
            # 导出材料
            "导出的 predict.py 接受 CSV 格式的传感器行，输出动作名称。"
            "在行空板等硬件上，读取真实传感器数据后传给 predict_raw()，"
            "即可实现实时决策控制——无需网络，离线运行。",
        ],
        real_world_examples=[
            "空调根据温度、湿度自动决定「制冷 / 制热 / 待机」。",
            "扫地机器人遇到台阶（距离传感器突变）就停下，不会摔下去。",
            "农业大棚根据土壤湿度自动决定「浇水 / 不浇」。",
            "电梯综合各楼层的呼叫信号，决定先去哪一层。",
        ],
        common_mistakes=[
            "每种动作只给了极端值（只有「很热」和「很冷」），"
            "分界线附近（不冷不热）模型就不会判断了。数值范围要覆盖真实场景。",
            "某个动作的样本太少，模型对它的判断不可靠。每种动作多准备几行。",
        ],
        hands_on_experiments=[
            "读规则：训练后展开「决策规则」，对照你的数据，"
            "看模型学出的 if-else 是不是和你预想的一致。",
            "边界实验：用刚好卡在分界线上的数值去测试，看模型判断得合不合理。",
            "看重要性：训练后看「各传感器重要程度」，"
            "哪个传感器对决策的影响最大？和你的直觉一样吗？",
        ],
        next_steps=(
            "决策树最大的优点是「规则看得见」。如果数据更复杂，"
            "可以在训练页换「梯度提升」等更强的算法试试（准确率可能更高，但规则变成黑箱）。"
            "想了解神经网络为什么是「黑箱」，去「深度学习地图」。"
        ),
    ),
    TaskDefinition(
        slug="general_object_detector",
        title="目标检测",
        summary="上传图片、把目标框出来，训练一个能在新图上自动框出目标的检测模型。",
        student_goal="理解目标检测：不只认出「是什么」，还要框出「在哪」。",
        group="通用练习",
        requirement_source="机器学习基础练习",
        competition_requirements=[
            "上传图片，把要识别的目标用框圈出来（每类多框几张）",
            "选「轻量检测」算法，点训练",
            "用一张新图测试，看模型画出的框",
            "观察漏检 / 误检 / 框偏，回头补数据",
        ],
        ai_capability="object_detector_trainable",
        sample_dataset_kind="detect",
        runtime_requirements=["scikit-learn", "joblib", "numpy", "pillow", "onnxruntime"],
        voice_profile="none",
        paused_features=[],
        suggested_hardware=["student_laptop"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "上传图片",
            "在图上框出目标并选类别",
            "选「轻量检测」点训练",
            "上传新图测试，看画框",
            "导出材料包（下一期上线）",
        ],
        concept_intro=(
            "目标检测让计算机不只说出「图里有什么」，还要指出「每个东西在哪」——用一个框圈住它。"
            "这比分类难：要同时回答「在哪」和「是什么」。"
            "本平台的「轻量检测」用了一个聪明的两步法：先借用预训练网络找出「这里好像有东西」的候选框，"
            "再训练一个分类器认出每个框里是什么。这正是检测最早的经典做法，有个名字叫 R-CNN。"
        ),
        step_guides=[
            # 准备数据
            "上传图片，在每张图上把要识别的目标用框圈出来，并给框选好类别。"
            "框要贴着目标的边缘——框太大留太多背景，模型会把背景也学进去；框漏了，模型会以为那也是背景。"
            "同一张图里同类目标要都框上；每类多框几张，目标的大小、角度多样些，模型才学得稳。",
            # 训练模型
            "选「轻量检测」再点训练。平台先把你框里的内容裁出来当正样本，"
            "再随机取一些你没框到的区域当「背景」，教模型认出每个候选框里装的是什么——这一步就是普通的分类，CPU 上几秒就训完。"
            "（卡片里的「YOLO」是更强的端到端做法，找框也自己学，但更重更慢，下一期接入。）",
            # 测试效果
            "上传一张新图，看模型画出的框，检查三点：找得到吗（有没有漏检）、"
            "框得准吗（位置贴不贴合）、认得对吗（标签和置信度对不对）。"
            "同一个目标有时会被框好几次，这些重叠的框平台会自动用 NMS（一种去重方法）只留最准的一个。"
            "如果总漏检某类，回第 1 步给它多框几张。",
            # 导出材料
            "导出会把训练好的检测模型和可运行脚本打包成材料包。"
            "（检测的导出包将在下一期上线，先把前三步——标注、训练、测试——玩透。）",
        ],
        real_world_examples=[
            "自动驾驶：实时框出路上的行人、车辆、红绿灯，才能做出反应。",
            "安防摄像头：框出画面里的每个人，自动数人数。",
            "手机相册：先框出照片里的人脸，再按人分组。",
            "工厂质检：框出产品上瑕疵的具体位置，而不只是说「这件有问题」。",
        ],
        common_mistakes=[
            "框画得太大、留了一大圈背景——模型会把背景也当成目标的一部分，换个背景就认错。框要贴着目标边缘。",
            "漏框：图里明明有目标却没框，模型会把它当成「背景」学进去，越学越乱。同一张图里同类目标要都框上。",
        ],
        hands_on_experiments=[
            "漏检实验：先每类只框 2–3 张训练，看新图上漏检多不多；再多框几张重训，对比漏检是不是变少了。",
            "框大小实验：故意把框画得很大（含很多背景）训练一次，再用贴边的框训练一次，比较两次画框的效果。",
            "候选框观察：测试时留意——有的目标没被框出来，往往是预训练网络压根没在那儿找出候选框（这是「轻量检测」的局限，YOLO 能改善）。",
        ],
        next_steps=(
            "你体验的是「轻量检测」——经典 R-CNN 的简化版（找框是借来的，你只训练「认框」）。"
            "想要更强的端到端检测（连「找框」也自己学），那就是 YOLO，下一期接入。"
            "检测和图像分类的关系、CNN 怎么看图，去「深度学习地图」第 3 节了解。"
        ),
    ),
]

GENERAL_ML = CompetitionDefinition(
    slug="general_ml",
    title="机器学习任务",
    summary="不挂竞赛的基础练习：图像分类、文本分类、智能问答、传感器决策。",
    tasks=GENERAL_TASKS,
)

COMPETITIONS = [
    CompetitionDefinition(
        slug="smart_museum",
        title="智能博物",
        summary="适合先验证轻量工作流：文本分类、知识问答、作品材料整理。",
        tasks=SMART_MUSEUM_TASKS,
    ),
    CompetitionDefinition(
        slug="future_creator",
        title="优创未来",
        summary="面向硬件和应用编程：图像识别、传感器决策、边缘部署准备。",
        tasks=FUTURE_CREATOR_TASKS,
    ),
]


def normalize_edition(edition: AppEdition | str | None = "all") -> AppEdition:
    if edition in ("smart_museum", "future_creator"):
        return edition
    return "all"


def list_competitions(edition: AppEdition | str | None = "all") -> list[CompetitionDefinition]:
    normalized = normalize_edition(edition)
    if normalized == "all":
        return COMPETITIONS
    return [competition for competition in COMPETITIONS if competition.slug == normalized]


def get_competition(
    slug: str,
    edition: AppEdition | str | None = "all",
) -> CompetitionDefinition | None:
    # 通用任务组在所有版本都可用，不参与竞赛版本过滤。
    if slug == GENERAL_ML.slug:
        return GENERAL_ML
    return next((competition for competition in list_competitions(edition) if competition.slug == slug), None)


def get_task(
    competition_slug: str,
    task_slug: str,
    edition: AppEdition | str | None = "all",
) -> TaskDefinition | None:
    competition = get_competition(competition_slug, edition)
    if competition is None:
        return None
    return next((task for task in competition.tasks if task.slug == task_slug), None)
