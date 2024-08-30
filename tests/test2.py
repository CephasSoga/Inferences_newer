from transformers import pipeline
import time

summarizer = pipeline("summarization")

text = """
Artificial Intelligence (AI) has become a key technology in the modern world. Its applications range from healthcare 
to finance, and its impact is growing exponentially. As AI continues to develop, the ethical implications of its use 
become more significant. Many experts are calling for regulations to ensure AI is used responsibly. Despite these 
concerns, the benefits of AI are clear. It has the potential to revolutionize industries, improve efficiency, and 
solve complex problems. However, the challenges associated with AI, such as bias in decision-making and the potential 
for job displacement, must be addressed. The future of AI will depend on finding the right balance between innovation 
and responsibility.
"""
s = time.perf_counter()
summary = summarizer(text, max_length=50, min_length=25, do_sample=False)
print(summary[0]['summary_text'])
e = time.perf_counter()

print(f"Execution time: {e-s:0.4f} seconds")
