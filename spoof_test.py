import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, precision_recall_curve, roc_curve, auc
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import seaborn as sns
from tqdm import tqdm

from detector.ultralight import FaceDetector
from antispoof.Fasnet import Fasnet

def load_test_images(base_dir="spoofing_test"):
    """
    Load images from real and fake folders with their labels
    
    Args:
        base_dir: Base directory containing 'real' and 'fake' folders
        
    Returns:
        List of tuples (image_path, is_real)
    """
    real_dir = os.path.join(base_dir, "real")
    fake_dir = os.path.join(base_dir, "fake")
    
    test_data = []
    
    # Load real images
    if os.path.exists(real_dir):
        real_images = [os.path.join(real_dir, f) for f in os.listdir(real_dir) 
                       if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        test_data.extend([(img_path, True) for img_path in real_images])
    
    # Load fake images
    if os.path.exists(fake_dir):
        fake_images = [os.path.join(fake_dir, f) for f in os.listdir(fake_dir) 
                       if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        test_data.extend([(img_path, False) for img_path in fake_images])
    
    return test_data

def evaluate_antispoofing():
    """
    Evaluate anti-spoofing system performance on test images
    """
    # Initialize models
    models_dir = "model"
    first_model = os.path.join(models_dir, "2.7_80x80_MiniFASNetV2.pth")
    second_model = os.path.join(models_dir, "4_0_0_80x80_MiniFASNetV1SE.pth")
    detector_model = os.path.join(models_dir, "version-RFB-320_without_postprocessing.tflite")
    
    # Load models
    fasnet = Fasnet(first_model, second_model)
    detector = FaceDetector(detector_model, conf_threshold=0.7)
    
    # Load test data
    test_data = load_test_images()
    if not test_data:
        print("❌ No test images found in spoofing_test directory")
        return
    
    print(f"📊 Testing {len(test_data)} images ({sum(1 for _, is_real in test_data if is_real)} real, "
          f"{sum(1 for _, is_real in test_data if not is_real)} fake)")
    
    # Initialize results containers
    y_true = []  # Ground truth labels (True = real, False = fake)
    y_pred = []  # Predicted labels (True = real, False = fake)
    scores = []  # Confidence scores for ROC curve
    results = []  # For detailed results logging
    
    # Process each image
    for img_path, is_real_gt in tqdm(test_data, desc="Testing images"):
        try:
            # Load image
            image = cv2.imread(img_path)
            if image is None:
                print(f"⚠️ Could not read image: {img_path}")
                continue
                
            # Detect faces
            boxes, scores_det = detector.detect_faces(image)
            if len(boxes) == 0:
                print(f"⚠️ No face detected in {img_path}")
                continue
                
            # Use the face with highest confidence
            highest_score_idx = np.argmax(scores_det)
            box = boxes[highest_score_idx].astype(int)
            x, y, w, h = box[0], box[1], box[2] - box[0], box[3] - box[1]
            
            # Analyze with anti-spoofing
            is_real_pred, score = fasnet.analyze(image, (x, y, w, h))
            
            # Record results
            y_true.append(is_real_gt)
            y_pred.append(is_real_pred)
            scores.append(score if is_real_pred else 1-score)  # Use probability of being real
            
            # Store detailed result for logging
            results.append({
                "path": img_path,
                "ground_truth": "real" if is_real_gt else "fake",
                "prediction": "real" if is_real_pred else "fake",
                "score": score,
                "correct": is_real_gt == is_real_pred
            })
            
        except Exception as e:
            print(f"❌ Error processing {img_path}: {str(e)}")
    
    if not y_true:
        print("❌ No valid results to evaluate")
        return
        
    # Calculate metrics
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    
    # Standard metrics
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    
    # Security metrics
    far = fp / (fp + tn)  # False Acceptance Rate (fake accepted as real)
    frr = fn / (fn + tp)  # False Rejection Rate (real rejected as fake)
    
    # Calculate EER
    fpr, tpr, thresholds = roc_curve(y_true, scores)
    fnr = 1 - tpr
    eer_threshold = thresholds[np.nanargmin(np.absolute(fnr - fpr))]
    eer = np.mean([fpr[np.nanargmin(np.absolute(fnr - fpr))], 
                   fnr[np.nanargmin(np.absolute(fnr - fpr))]])
    
    # Print results
    print("\n======= ANTI-SPOOFING EVALUATION RESULTS =======")
    print(f"Total images processed: {len(y_true)}")
    print(f"Real images: {sum(y_true)}")
    print(f"Fake images: {len(y_true) - sum(y_true)}")
    print("\nConfusion Matrix:")
    print(f"TN: {tn} | FP: {fp}")
    print(f"FN: {fn} | TP: {tp}")
    print("\nStandard Metrics:")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1 Score: {f1:.4f}")
    print("\nSecurity Metrics:")
    print(f"False Acceptance Rate (FAR): {far:.4f}")
    print(f"False Rejection Rate (FRR): {frr:.4f}")
    print(f"Equal Error Rate (EER): {eer:.4f} at threshold {eer_threshold:.4f}")
    
    # Plot confusion matrix
    plt.figure(figsize=(10, 8))
    
    plt.subplot(2, 2, 1)
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", 
                xticklabels=["Fake", "Real"], 
                yticklabels=["Fake", "Real"])
    plt.title("Confusion Matrix")
    plt.ylabel("True Label")
    plt.xlabel("Predicted Label")
    
    # Plot ROC curve
    plt.subplot(2, 2, 2)
    plt.plot(fpr, tpr, label=f'AUC = {auc(fpr, tpr):.4f}')
    plt.plot([0, 1], [0, 1], 'k--')
    plt.title('ROC Curve')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.legend()
    
    # Plot FAR vs FRR curve
    plt.subplot(2, 2, 3)
    plt.plot(thresholds, fpr, label='FAR')
    plt.plot(thresholds, fnr, label='FRR')
    plt.axvline(x=eer_threshold, color='r', linestyle='--', 
                label=f'EER = {eer:.4f} at {eer_threshold:.2f}')
    plt.title('FAR-FRR Curve')
    plt.xlabel('Threshold')
    plt.ylabel('Error Rate')
    plt.legend()
    
    # Plot precision-recall curve
    plt.subplot(2, 2, 4)
    precision_curve, recall_curve, _ = precision_recall_curve(y_true, scores)
    plt.plot(recall_curve, precision_curve, 
             label=f'AP = {auc(recall_curve, precision_curve):.4f}')
    plt.title('Precision-Recall Curve')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig("antispoofing_evaluation.png")
    print(f"✅ Evaluation charts saved to antispoofing_evaluation.png")
    
    # Save detailed results
    plt.figure(figsize=(12, 6))
    
    # Plot success and error examples
    correct_reals = [r for r in results if r["ground_truth"] == "real" and r["correct"]]
    false_rejects = [r for r in results if r["ground_truth"] == "real" and not r["correct"]]
    correct_fakes = [r for r in results if r["ground_truth"] == "fake" and r["correct"]]
    false_accepts = [r for r in results if r["ground_truth"] == "fake" and not r["correct"]]
    
    # Log examples of errors and successes
    print("\n===== ERROR EXAMPLES =====")
    print("False Rejections (Real detected as Fake):")
    for i, example in enumerate(false_rejects[:5]):
        print(f"{i+1}. {example['path']} (Score: {example['score']:.4f})")
        
    print("\nFalse Acceptances (Fake detected as Real):")
    for i, example in enumerate(false_accepts[:5]):
        print(f"{i+1}. {example['path']} (Score: {example['score']:.4f})")
        
    # Save results to CSV
    import csv
    with open("antispoofing_results.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Image Path", "Ground Truth", "Prediction", "Score", "Correct"])
        for r in results:
            writer.writerow([
                r["path"], 
                r["ground_truth"], 
                r["prediction"], 
                f"{r['score']:.4f}", 
                r["correct"]
            ])
    print(f"✅ Detailed results saved to antispoofing_results.csv")

if __name__ == "__main__":
    evaluate_antispoofing()