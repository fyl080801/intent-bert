#!/bin/bash
#
# 提交 BERT 微调训练工作流
# 使用 bert-training-universal.yaml 实现参数化微调
#

set -e

# ==================== 默认配置 ====================
NAMESPACE="dev"
WORKFLOW_FILE="bert-training-universal.yaml"
DATASET_NAME="financial_intent_fixed"
MODEL_NAME="hfl/chinese-roberta-wwm-ext"
WATCH=false

# ==================== 函数定义 ====================

usage() {
    cat << EOF
用法: $0 [选项]

提交通用BERT微调训练工作流

选项:
    -n, --namespace <namespace>        Kubernetes 命名空间 (默认: dev)
    -d, --dataset <name>               数据集名称 (默认: financial_intent_fixed)
                                        可选值: financial_intent_fixed, financial_intent_dynamic, jd_sentiment
    -m, --model <name>                 预训练模型名称 (默认: hfl/chinese-roberta-wwm-ext)
    -b, --batch-size <size>            批次大小 (覆盖数据集配置)
    -e, --epochs <num>                 训练轮数 (覆盖数据集配置)
    -l, --learning-rate <rate>         学习率 (覆盖数据集配置)
    --max-length <len>                 最大序列长度 (覆盖数据集配置)
    -w, --watch                        实时监控工作流
    -h, --help                         显示此帮助信息

示例:
    # 使用默认配置训练 financial_intent_fixed
    $0

    # 训练 jd_sentiment 数据集并监控
    $0 -d jd_sentiment -w

    # 自定义批次大小和训练轮数
    $0 -b 32 -e 10

    # 使用不同的模型
    $0 -m bert-base-chinese

EOF
    exit 1
}

info() {
    echo "ℹ️  $1"
}

success() {
    echo "✅ $1"
}

error() {
    echo "❌ $1" >&2
    exit 1
}

# ==================== 参数解析 ====================

while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -d|--dataset)
            DATASET_NAME="$2"
            shift 2
            ;;
        -m|--model)
            MODEL_NAME="$2"
            shift 2
            ;;
        -b|--batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        -e|--epochs)
            NUM_EPOCHS="$2"
            shift 2
            ;;
        -l|--learning-rate)
            LEARNING_RATE="$2"
            shift 2
            ;;
        --max-length)
            MAX_LENGTH="$2"
            shift 2
            ;;
        -w|--watch)
            WATCH=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            error "未知参数: $1"
            ;;
    esac
done

# ==================== 验证环境 ====================

# 检查 kubectl
if ! command -v kubectl &> /dev/null; then
    error "kubectl 未安装或不在 PATH 中"
fi

# 检查 argo
if ! command -v argo &> /dev/null; then
    error "argo 未安装或不在 PATH 中"
fi

# 检查工作流文件
if [ ! -f "$WORKFLOW_FILE" ]; then
    error "工作流文件不存在: $WORKFLOW_FILE"
fi

# 检查数据集注册表
if [ ! -f "../datasets/dataset_registry.json" ]; then
    error "数据集注册表不存在: ../datasets/dataset_registry.json"
fi

# 验证数据集名称
if ! jq -e ".datasets.\"$DATASET_NAME\"" ../datasets/dataset_registry.json > /dev/null 2>&1; then
    error "数据集 '$DATASET_NAME' 在注册表中不存在"
fi

# ==================== 构建参数 ====================

WORKFLOW_NAME="bert-train-${DATASET_NAME}-$(date +%s)"
PARAMS=""

PARAMS="$PARAMS -p dataset_name=$DATASET_NAME"
PARAMS="$PARAMS -p model_name=$MODEL_NAME"

# 添加可选参数（如果设置了）
if [ -n "$BATCH_SIZE" ]; then
    PARAMS="$PARAMS -p batch_size=$BATCH_SIZE"
fi

if [ -n "$NUM_EPOCHS" ]; then
    PARAMS="$PARAMS -p num_epochs=$NUM_EPOCHS"
fi

if [ -n "$LEARNING_RATE" ]; then
    PARAMS="$PARAMS -p learning_rate=$LEARNING_RATE"
fi

if [ -n "$MAX_LENGTH" ]; then
    PARAMS="$PARAMS -p max_length=$MAX_LENGTH"
fi

# ==================== 提交工作流 ====================

info "命名空间: $NAMESPACE"
info "数据集: $DATASET_NAME"
info "模型: $MODEL_NAME"
info "工作流文件: $WORKFLOW_FILE"
echo ""

# 提交工作流
info "提交工作流..."
WORKFLOW_OUTPUT=$(argo submit \
    --namespace "$NAMESPACE" \
    --name "$WORKFLOW_NAME" \
    $PARAMS \
    "$WORKFLOW_FILE" 2>&1)

WORKFLOW_STATUS=$?

if [ $WORKFLOW_STATUS -ne 0 ]; then
    error "工作流提交失败:\n$WORKFLOW_OUTPUT"
fi

# 提取工作流名称
SUBMITTED_NAME=$(echo "$WORKFLOW_OUTPUT" | grep -oP 'Name:\s*\K\S+' || echo "$WORKFLOW_NAME")

success "工作流已提交: $SUBMITTED_NAME"

# ==================== 监控工作流 ====================

if [ "$WATCH" = true ]; then
    info "监控工作流执行状态..."
    echo ""
    argo watch --namespace "$NAMESPACE" "$SUBMITTED_NAME"
else
    info "使用以下命令查看工作流状态:"
    echo "  argo get --namespace $NAMESPACE $SUBMITTED_NAME"
    echo ""
    info "使用以下命令查看工作流日志:"
    echo "  argo logs --namespace $NAMESPACE $SUBMITTED_NAME"
    echo ""
    info "使用以下命令实时监控:"
    echo "  argo watch --namespace $NAMESPACE $SUBMITTED_NAME"
fi
