from __future__ import annotations

from app.models import AppEdition, CompetitionDefinition, TaskDefinition

STANDARD_OUTPUTS = [
    "README.md",
    "train.py",
    "predict.py",
    "run.py",
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
]


SMART_MUSEUM_TASKS = [
    TaskDefinition(
        slug="heritage_text_classifier",
        title="非遗词语分类工作流",
        summary="把少量非遗词语或说明文本整理成可运行的分类示例。",
        student_goal="生成一个能读取文本、匹配类别并输出结果的轻量 Python 程序。",
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
            "填写类别名称",
            "准备少量样例文本",
            "生成脚本和 Notebook",
            "在电脑上运行验证",
            "把结果文件放入比赛作品",
        ],
    ),
    TaskDefinition(
        slug="heritage_qa_helper",
        title="非遗知识问答模板",
        summary="把竞赛知识材料整理成固定问答程序模板。",
        student_goal="生成一个可修改的问答检索脚本，帮助快速完成知识展示任务。",
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
            "选择非遗宣传场景",
            "整理知识点和交互问题",
            "生成问答脚本",
            "补充作品照片和说明",
            "导出提交材料",
        ],
    ),
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
        runtime_requirements=["scikit-learn", "joblib", "numpy", "pillow"],
        voice_profile="dfrobot_tts_broadcast",
        paused_features=["摄像头实时拍照"],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "录入5张人脸卡片信息",
            "填写姓名和简介",
            "生成识别结果模板",
            "连接显示和播报模块",
            "导出挑战一材料",
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
            "填写正确知识卡片文本",
            "准备错误文本样例",
            "生成错别字比对脚本",
            "验证播报格式",
            "导出挑战二材料",
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
            "填写类别和非遗名称",
            "准备句子样例",
            "生成分类脚本",
            "验证输出格式",
            "导出挑战四材料",
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
        runtime_requirements=["scikit-learn", "joblib", "numpy", "pillow"],
        voice_profile="none",
        paused_features=[],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "填写识别类别",
            "准备图片样例",
            "生成推理脚本",
            "本机运行检查",
            "按硬件说明迁移",
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
        runtime_requirements=["scikit-learn", "joblib", "numpy", "pandas"],
        voice_profile="none",
        paused_features=["真实传感器连接", "真实执行器控制"],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "选择医疗应用场景",
            "填写输入信号",
            "填写输出动作",
            "生成控制脚本",
            "整理提交材料",
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
        runtime_requirements=["scikit-learn", "joblib", "numpy", "pillow"],
        voice_profile="unihiker_keyword_voice",
        paused_features=[],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "填写现场关键词",
            "选择1类卡片",
            "生成语音互动模板",
            "生成图像识别占位接口",
            "整理小学组提交材料",
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
        runtime_requirements=["scikit-learn", "joblib", "numpy", "pillow"],
        voice_profile="unihiker_keyword_voice",
        paused_features=[],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "填写现场关键词",
            "选择2类卡片",
            "生成训练数据目录",
            "生成模型调用脚本",
            "整理初中组提交材料",
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
        runtime_requirements=["scikit-learn", "joblib", "numpy", "pillow"],
        voice_profile="unihiker_keyword_voice",
        paused_features=["真实大模型智能体", "真实机械装置控制", "行空板M10本地大模型需外接服务或后续扩展"],
        suggested_hardware=["unihiker_m10"],
        required_outputs=STANDARD_OUTPUTS,
        starter_steps=[
            "设定医疗场景智能体角色",
            "选择2类卡片",
            "生成视觉识别接口",
            "生成运动控制伪代码",
            "整理高中组提交材料",
        ],
    ),
]

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
