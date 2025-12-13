@echo off
docker build -f Dockerfile.prod --build-arg "NEXT_PUBLIC_API_URL=http://bharatbuild-alb-223139118.ap-south-1.elb.amazonaws.com/api/v1" --build-arg "NEXT_PUBLIC_WS_URL=ws://bharatbuild-alb-223139118.ap-south-1.elb.amazonaws.com/ws" -t bharatbuild-frontend .
