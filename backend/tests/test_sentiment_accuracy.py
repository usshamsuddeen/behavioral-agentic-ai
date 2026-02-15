"""
Sentiment Analysis Accuracy Testing Suite
Tests BERT model performance against ground truth labeled data
Generates comprehensive accuracy reports per language
"""

import pytest
import pandas as pd
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.sentiment import analyze_sentiment
from app.nlp.transformer_sentiment import analyze_sentiment_transformer, is_model_available


class SentimentAccuracyTester:
    """Comprehensive sentiment accuracy testing framework"""
    
    def __init__(self, test_data_path: str):
        self.test_data_path = test_data_path
        self.df = None
        self.results = {
            'overall': {},
            'by_language': {},
            'by_sentiment': {},
            'confusion_matrix': {},
            'errors': []
        }
    
    def load_test_data(self) -> pd.DataFrame:
        """Load and validate test dataset"""
        try:
            self.df = pd.read_csv(self.test_data_path)
            print(f"[OK] Loaded {len(self.df)} test samples")
            print(f"   Languages: {self.df['language'].unique().tolist()}")
            print(f"   Distribution:")
            print(self.df['sentiment_category'].value_counts())
            return self.df
        except Exception as e:
            pytest.fail(f"Failed to load test data: {e}")
    
    def test_single_sample(self, text: str, language: str, ground_truth: int) -> Dict:
        """Test a single sample and return detailed results"""
        try:
            # Get sentiment analysis result
            result = analyze_sentiment(text, language)
            
            predicted_stars = result.get('star_rating', 3)
            predicted_sentiment = result.get('sentiment', 'neutral')
            confidence = result.get('confidence', 0.0)
            model_used = result.get('model', 'unknown')
            
            # Calculate accuracy metrics
            exact_match = predicted_stars == ground_truth
            off_by_1_match = abs(predicted_stars - ground_truth) <= 1
            
            # Map stars to sentiment category for category accuracy
            def stars_to_category(stars: int) -> str:
                if stars <= 2:
                    return 'negative'
                elif stars == 3:
                    return 'neutral'
                else:
                    return 'positive'
            
            predicted_category = stars_to_category(predicted_stars)
            actual_category = stars_to_category(ground_truth)
            category_match = predicted_category == actual_category
            
            return {
                'text': text[:50] + '...' if len(text) > 50 else text,
                'language': language,
                'ground_truth_stars': ground_truth,
                'predicted_stars': predicted_stars,
                'ground_truth_category': actual_category,
                'predicted_category': predicted_category,
                'exact_match': exact_match,
                'off_by_1_match': off_by_1_match,
                'category_match': category_match,
                'confidence': confidence,
                'model_used': model_used,
                'error': predicted_stars - ground_truth
            }
        except Exception as e:
            return {
                'text': text[:50],
                'language': language,
                'ground_truth_stars': ground_truth,
                'error_message': str(e),
                'exact_match': False,
                'off_by_1_match': False,
                'category_match': False
            }
    
    def run_full_evaluation(self) -> Dict:
        """Run complete evaluation on test dataset"""
        if self.df is None:
            self.load_test_data()
        
        print("\nRunning Sentiment Accuracy Evaluation...")
        print("=" * 60)
        
        all_results = []
        
        for idx, row in self.df.iterrows():
            result = self.test_single_sample(
                text=row['text'],
                language=row['language'],
                ground_truth=row['ground_truth_stars']
            )
            result['scenario_type'] = row.get('scenario_type', 'unknown')
            all_results.append(result)
            
            # Progress indicator
            if (idx + 1) % 20 == 0:
                print(f"   Processed {idx + 1}/{len(self.df)} samples...")
        
        # Calculate overall metrics
        self._calculate_metrics(all_results)
        
        return self.results
    
    def _calculate_metrics(self, all_results: List[Dict]):
        """Calculate comprehensive accuracy metrics"""
        total_samples = len(all_results)
        
        # Overall metrics
        exact_matches = sum(1 for r in all_results if r.get('exact_match', False))
        off_by_1_matches = sum(1 for r in all_results if r.get('off_by_1_match', False))
        category_matches = sum(1 for r in all_results if r.get('category_match', False))
        
        self.results['overall'] = {
            'total_samples': total_samples,
            'exact_match_count': exact_matches,
            'exact_match_accuracy': round(exact_matches / total_samples, 4),
            'off_by_1_count': off_by_1_matches,
            'off_by_1_accuracy': round(off_by_1_matches / total_samples, 4),
            'category_match_count': category_matches,
            'category_accuracy': round(category_matches / total_samples, 4),
            'average_confidence': round(sum(r.get('confidence', 0) for r in all_results) / total_samples, 4)
        }
        
        # Per-language metrics
        for language in self.df['language'].unique():
            lang_results = [r for r in all_results if r['language'] == language]
            lang_total = len(lang_results)
            
            lang_exact = sum(1 for r in lang_results if r.get('exact_match', False))
            lang_off_by_1 = sum(1 for r in lang_results if r.get('off_by_1_match', False))
            lang_category = sum(1 for r in lang_results if r.get('category_match', False))
            
            self.results['by_language'][language] = {
                'total_samples': lang_total,
                'exact_match_accuracy': round(lang_exact / lang_total, 4),
                'off_by_1_accuracy': round(lang_off_by_1 / lang_total, 4),
                'category_accuracy': round(lang_category / lang_total, 4),
                'average_confidence': round(sum(r.get('confidence', 0) for r in lang_results) / lang_total, 4)
            }
        
        # Per-sentiment category metrics
        for category in ['positive', 'neutral', 'negative']:
            cat_results = [r for r in all_results if r.get('ground_truth_category') == category]
            if cat_results:
                cat_total = len(cat_results)
                cat_correct = sum(1 for r in cat_results if r.get('category_match', False))
                
                self.results['by_sentiment'][category] = {
                    'total_samples': cat_total,
                    'category_accuracy': round(cat_correct / cat_total, 4),
                    'precision': self._calculate_precision(all_results, category),
                    'recall': round(cat_correct / cat_total, 4)
                }
        
        # Confusion matrix (stars)
        for actual in range(1, 6):
            self.results['confusion_matrix'][actual] = {}
            for predicted in range(1, 6):
                count = sum(1 for r in all_results 
                          if r['ground_truth_stars'] == actual and r.get('predicted_stars') == predicted)
                self.results['confusion_matrix'][actual][predicted] = count
        
        # Identify worst errors
        errors = [r for r in all_results if abs(r.get('error', 0)) >= 2]
        self.results['errors'] = sorted(errors, key=lambda x: abs(x.get('error', 0)), reverse=True)[:10]
    
    def _calculate_precision(self, all_results: List[Dict], category: str) -> float:
        """Calculate precision for a sentiment category"""
        predicted_as_category = [r for r in all_results if r.get('predicted_category') == category]
        if not predicted_as_category:
            return 0.0
        
        true_positives = sum(1 for r in predicted_as_category if r.get('ground_truth_category') == category)
        return round(true_positives / len(predicted_as_category), 4)
    
    def print_report(self):
        """Print comprehensive accuracy report"""
        results = self.results
        
        print("\n" + "=" * 70)
        print("SENTIMENT ANALYSIS ACCURACY REPORT")
        print("=" * 70)
        
        # Overall Results
        print("\n[OVERALL PERFORMANCE]:")
        overall = results['overall']
        print(f"   Total Samples: {overall['total_samples']}")
        print(f"   Exact Match Accuracy: {overall['exact_match_accuracy']*100:.2f}% ({overall['exact_match_count']}/{overall['total_samples']})")
        print(f"   Off-by-1 Accuracy: {overall['off_by_1_accuracy']*100:.2f}% ({overall['off_by_1_count']}/{overall['total_samples']})")
        print(f"   Category Accuracy: {overall['category_accuracy']*100:.2f}% ({overall['category_match_count']}/{overall['total_samples']})")
        print(f"   Average Confidence: {overall['average_confidence']*100:.2f}%")
        
        # Target comparison
        print("\n[TARGET COMPARISON]:")
        print(f"   BERT Published Off-by-1: 94.3%")
        print(f"   Our Off-by-1 Accuracy: {overall['off_by_1_accuracy']*100:.2f}%")
        if overall['off_by_1_accuracy'] >= 0.90:
            print("   [PASS] Meets 90% threshold")
        else:
            print("   [WARNING] Below 90% threshold")
        
        # Per-Language Results
        print("\n[PER-LANGUAGE PERFORMANCE]:")
        print(f"   {'Language':<10} {'Exact':<10} {'Off-by-1':<10} {'Category':<10} {'Confidence':<10}")
        print(f"   {'-'*58}")
        for lang, metrics in results['by_language'].items():
            print(f"   {lang:<10} {metrics['exact_match_accuracy']*100:>6.2f}%   "
                  f"{metrics['off_by_1_accuracy']*100:>6.2f}%   "
                  f"{metrics['category_accuracy']*100:>6.2f}%   "
                  f"{metrics['average_confidence']*100:>6.2f}%")
        
        # Per-Sentiment Category
        print("\n[PER-SENTIMENT PERFORMANCE]:")
        print(f"   {'Category':<10} {'Accuracy':<10} {'Precision':<10} {'Recall':<10}")
        print(f"   {'-'*40}")
        for category, metrics in results['by_sentiment'].items():
            print(f"   {category:<10} {metrics['category_accuracy']*100:>6.2f}%   "
                  f"{metrics['precision']*100:>6.2f}%   {metrics['recall']*100:>6.2f}%")
        
        # Confusion Matrix
        print("\n[CONFUSION MATRIX (Actual -> Predicted)]:")
        print(f"   {'Actual':<8}", end='')
        for p in range(1, 6):
            print(f"{'*'*p:<6}", end='')
        print()
        print(f"   {'-'*48}")
        
        for actual in range(1, 6):
            print(f"   {'*'*actual:<8}", end='')
            for predicted in range(1, 6):
                count = results['confusion_matrix'][actual][predicted]
                print(f"{count:<6}", end='')
            print()
        
        # Worst Errors
        if results['errors']:
            print("\n[WORST PREDICTION ERRORS]:")
            for i, error in enumerate(results['errors'][:5], 1):
                print(f"\n   {i}. Language: {error['language']}")
                print(f"      Text: {error['text']}")
                print(f"      Ground Truth: {error['ground_truth_stars']} stars ({error['ground_truth_category']})")
                print(f"      Predicted: {error.get('predicted_stars', 'N/A')} stars ({error.get('predicted_category', 'N/A')})")
                print(f"      Error: {error.get('error', 'N/A')} stars off")
        
        print("\n" + "=" * 70)
    
    def save_results(self, output_path: str):
        """Save results to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n[SAVED] Results saved to: {output_path}")


# Pytest test functions
@pytest.fixture(scope="module")
def tester():
    """Create tester instance"""
    test_data_path = Path(__file__).parent / "data" / "sentiment_test_set.csv"
    return SentimentAccuracyTester(str(test_data_path))


def test_load_test_data(tester):
    """Test that test dataset loads correctly"""
    df = tester.load_test_data()
    assert len(df) > 0, "Test dataset is empty"
    assert 'language' in df.columns, "Missing language column"
    assert 'text' in df.columns, "Missing text column"
    assert 'ground_truth_stars' in df.columns, "Missing ground_truth_stars column"
    
    # Check all languages present
    expected_languages = {'en', 'es', 'fr', 'de', 'it', 'nl'}
    actual_languages = set(df['language'].unique())
    assert expected_languages == actual_languages, f"Missing languages: {expected_languages - actual_languages}"


def test_overall_accuracy(tester):
    """Test overall sentiment accuracy meets minimum thresholds"""
    results = tester.run_full_evaluation()
    tester.print_report()
    
    overall = results['overall']
    
    # Assert minimum accuracy thresholds
    assert overall['off_by_1_accuracy'] >= 0.85, \
        f"Off-by-1 accuracy {overall['off_by_1_accuracy']*100:.2f}% below 85% threshold"
    
    assert overall['category_accuracy'] >= 0.80, \
        f"Category accuracy {overall['category_accuracy']*100:.2f}% below 80% threshold"
    
    # Informational: exact match (not a hard requirement)
    print(f"\nℹ️ Exact match accuracy: {overall['exact_match_accuracy']*100:.2f}%")
    if overall['exact_match_accuracy'] >= 0.60:
        print("   ✅ Matches BERT's published 60.2% average")
    
    # Save results
    output_path = Path(__file__).parent / "results" / f"sentiment_accuracy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.parent.mkdir(exist_ok=True)
    tester.save_results(str(output_path))


def test_per_language_accuracy(tester):
    """Test that each language meets minimum accuracy"""
    if tester.results == {}:
        tester.run_full_evaluation()
    
    for language, metrics in tester.results['by_language'].items():
        # Each language should have reasonable off-by-1 accuracy
        assert metrics['off_by_1_accuracy'] >= 0.80, \
            f"Language {language} off-by-1 accuracy {metrics['off_by_1_accuracy']*100:.2f}% below 80%"


def test_category_balance(tester):
    """Test that all sentiment categories are recognized"""
    if tester.results == {}:
        tester.run_full_evaluation()
    
    # Check all categories have results
    assert 'positive' in tester.results['by_sentiment'], "Missing positive sentiment results"
    assert 'neutral' in tester.results['by_sentiment'], "Missing neutral sentiment results"
    assert 'negative' in tester.results['by_sentiment'], "Missing negative sentiment results"
    
    # Each category should have decent accuracy
    for category, metrics in tester.results['by_sentiment'].items():
        assert metrics['category_accuracy'] >= 0.75, \
            f"Category {category} accuracy {metrics['category_accuracy']*100:.2f}% below 75%"


def test_model_availability():
    """Test if BERT model is available"""
    available = is_model_available()
    if available:
        print("\n[OK] BERT model is loaded and available")
    else:
        print("\n[WARNING] BERT model not available, using fallback")
        pytest.skip("BERT model not available for testing")


if __name__ == "__main__":
    # Run as standalone script
    print("Starting Sentiment Accuracy Testing Suite")
    
    test_data_path = Path(__file__).parent / "data" / "sentiment_test_set.csv"
    tester = SentimentAccuracyTester(str(test_data_path))
    
    # Load data
    tester.load_test_data()
    
    # Run evaluation
    tester.run_full_evaluation()
    
    # Print report
    tester.print_report()
    
    # Save results
    output_path = Path(__file__).parent / "results" / f"sentiment_accuracy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tester.save_results(str(output_path))
    
    print("\nTesting complete!")

