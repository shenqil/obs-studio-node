## 初始化

```
yarn install
git submodule update --init --recursive
```

## 编译 arm64 版本

```
mkdir build-arm64
cd build-arm64
cmake .. -DCMAKE_INSTALL_PREFIX="$(pwd)/../dist/arm64" -DCMAKE_OSX_ARCHITECTURES=arm64 -G Xcode
cmake --build . --target install --config RelWithDebInfo
```

## 编译 x64 版本

```
mkdir build-x64
cd build-x64
cmake .. -DCMAKE_INSTALL_PREFIX="$(pwd)/../dist/x64" -DCMAKE_OSX_ARCHITECTURES=x86_64 -G Xcode
cmake --build . --target install --config RelWithDebInfo
```

## 合并为 Universal 版本

```
python3 ./ci/create-universal.py
```
