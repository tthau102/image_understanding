import json
import boto3
import base64

#
session = boto3.Session()
bedrock = session.client(service_name='bedrock-runtime') #creates a Bedrock client

#
models = [
    "apac.amazon.nova-pro-v1:0",
    "apac.anthropic.claude-3-5-sonnet-20241022-v2:0"
]

model = 1
bedrock_model_id = models[model] #set the foundation model

prompt = "What is the largest city in New Hampshire?" #the prompt to send to the model

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf8') 

bodys = [
    {
        "inferenceConfig": {
        "max_new_tokens": 1000
        },
        "messages": [
        {
            "role": "user",
            "content": [
            {
                "text": "Print result in very raw json format for programmatic perpose only, nothing any, no '```json', no '\','\n'"
            }
            ]
        }
        ]
    },
    {
        "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "top_k": 250,
            "stop_sequences": [],
            "temperature": 1,
            "top_p": 0.999,
            "messages": [
                {
                    "role": "user",
                    "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_to_base64("boncha_vietquat.jpg")
                        }
                    },
                    {
                        "type": "text",
                        "text": """
Look, describe and remember the item.
"""
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_to_base64("tumat.jpg")
                        }
                    },
                    {
                        "type": "text",
                        "text": """
Count the remembered item in this fridge
"""
                    }
                    ]
                }
            ]
    }
]

body = json.dumps(bodys[model])

#
response = bedrock.invoke_model(body=body, modelId=bedrock_model_id, accept='application/json', contentType='application/json') #send the payload to Amazon Bedrock

#
response_body = json.loads(response.get('body').read()) # read the response

# print(response_body)

print(response_body["content"][0]["text"])

# print(response_body["output"]["message"]["content"][0]["text"])

# with open("response.json", "w") as f:
#     f.write(json.dumps(response_body["output"]["message"]["content"][0]["text"], indent=4))

# response_text = response_body["results"][0]["outputText"] #extract the text from the JSON response

# print(response_text)
