from django.shortcuts import render,redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json
from pytube import YouTube
import assemblyai as aai
import openai
import os
import replicate
from .models import BlogPost
# Create your views here.

os.environ['REPLICATE_API_TOKEN'] = 'r8_6nkdIXLD3OcUXwRaxBUDQmsEtV38dAz01oeb9'

def yt_title(link):
    return YouTube(link).title

@login_required
def index(request):
    return render(request,'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            link = yt_title(yt_link)
            return JsonResponse({'error':'Invalid data sent'},status=400)

        
        
            # get yt title
        title = yt_title(yt_link)

            # get video transcript

        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error':'Failed to get transcript '},status=500)
        print(transcription)
            # use OpenAI to generate a blog

        blog_content = generate_blog_from_transcript(transcription)
        print(blog_content)
        if not blog_content:
            return JsonResponse({'error':'Failed to get blog content '},status=500)
            # save blog to database 
        new_article = BlogPost.objects.create(
            user=request.user,
            yt_title=title,
            yt_link=yt_link,
            generated_content=blog_content,
        )
        new_article.save()
        
            # return blog article as a response to frontend

        return JsonResponse({'content':blog_content})

    else:
        return JsonResponse({'error':'Invalid request method'},status=405)

def get_transcription(link):
    audio_file = downlaod_audio(link)
    aai.settings.api_key = "ad715fbb6eb4469eac49ca1fd4f07fae"
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)
    return transcript.text
    

def generate_blog_from_transcript(transcript):
    api_key = 'r8_6nkdIXLD3OcUXwRaxBUDQmsEtV38dAz01oeb9'
    pre_prompt = transcript
    prompt_input = "Kindly Gennerate a concise Blog from the provided article of text before."

# Generate LLM response
    output = replicate.run('a16z-infra/llama13b-v2-chat:df7690f1994d94e96ad9d568eac121aecf50684a0b0963b25a41cc40061269e5', # LLM model
                        input={"prompt": f"{pre_prompt} {prompt_input} Assistant: ", # Prompts
                        "temperature":0.2, "top_p":0.9, "max_length":128, "repetition_penalty":1})  # Model parameters
     
    full_response = ""

    for item in output:
        full_response += item
        
    return full_response


def downlaod_audio(link):
    yt = YouTube(link)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path=settings.MEDIA_ROOT)
    base , ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file,new_file)
    return new_file

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request,username=username,password=password)
        if user is not None:
            login(request,user)
            return redirect('/')
        else:
            error_message = 'Invalid Username or Password'
            return render(request,'login.html',{'error_message':error_message})
    return render(request,'login.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatPassword']
        if password == repeatPassword:
            try:
                user = User.objects.create_user(username,email,password)
                user.save()
                login(request,user)
                return redirect('/')
            except:
                error_message = 'Error bitch'
                return render(request,'signup.html' ,{'error_message': error_message})
        else:
            error_message = 'Passwords donot match'
            return render(request,'signup.html' ,{'error_message': error_message})
    return render(request,'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')

def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render("all-blogs.html",{'blog_articles':blog_articles})

def blog_details(request,pk):
    blog_article_detail = BlogPost.objects.filter(id=pk)
    if request.user == blog_article_detail.user:
        return render('blog-details.html',{'blog_article_detail':blog_article_detail})
    else:
        return render('/')