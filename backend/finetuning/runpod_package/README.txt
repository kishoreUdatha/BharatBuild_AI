============================================================
  BharatBuild AI - RunPod Training Package
============================================================

CONTENTS:
  - ultimate/train.jsonl    : 27,407 training samples
  - ultimate/eval.jsonl     : 3,046 evaluation samples
  - train.py                : Training script
  - inference.py            : Inference/testing script
  - runpod_train.sh         : One-click training script
  - requirements.txt        : Python dependencies

QUICK START:
============

1. Upload this folder to RunPod:
   - Use RunPod file browser, or
   - SCP: scp -r runpod_package root@YOUR_POD_IP:/workspace/

2. Connect to your pod (Web Terminal or SSH)

3. Run these commands:

   cd /workspace/runpod_package
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Start training
   python train.py \
       --train-file ./ultimate/train.jsonl \
       --eval-file ./ultimate/eval.jsonl \
       --model Qwen/Qwen2.5-Coder-7B-Instruct \
       --epochs 3 \
       --batch-size 2 \
       --output-dir ./output

4. Training takes ~4-6 hours on RTX 4090

5. Test the model:
   python inference.py --model-path ./output/final --interactive

6. Download trained model:
   scp -r root@YOUR_POD_IP:/workspace/runpod_package/output ./

============================================================
