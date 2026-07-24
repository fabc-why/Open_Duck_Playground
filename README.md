# Open Duck Playground (Forked Version)

This repository is a fork of the original project:

👉 https://github.com/apirrone/Open_Duck_Playground

## 📌 About this Repository

This project is based on the excellent work by [apirrone](https://github.com/apirrone).  
The original repository provided the foundation for this fork, and we build upon it with modifications, improvements, and experiments.

## 🔀 Fork Information

- **Original Repository**: https://github.com/apirrone/Open_Duck_Playground  
- **Forked From**: apirrone/Open_Duck_Playground  
- **Purpose of Fork**:
  - Custom modifications
  - Feature experiments
  - Personal improvements / extensions

## ⚙️ Changes in This Fork

Compared to the original repository, this fork includes:

- ✅ Enable Joustick controller  
- ✅ Add camera to head
- ✅ Some changes for tele-operation

## 🛠 インストール方法

### 前提

- Ubuntu 22.04 が基本ですが、26.04 でも動作することを確認していますので、Ubuntu系なら27以降もいけるでしょう（多分）。
- それなりの GPU 性能が必要です。詳細な要件は fork 元の Open Duck Playground を参照してください。
- `uv` というツールを入れる。
- VS Code は必須ではありませんが、あると作業しやすいです。

### 通常版の起動

1. リポジトリを clone します。

  ```bash
  git https://github.com/fabc-why/Open_Duck_Playground.git
  cd Open_Duck_Playground
  ```

2. `uv sync` を実行します。

  ```bash
  uv sync
  ```

  `pyproject.toml` に書かれている Python バージョンや依存ライブラリがまとめて入ります。

3. `playground/open_duck_mini_v2/mujoco_infer.py` を実行します。

  ```bash
  uv run python playground/open_duck_mini_v2/mujoco_infer.py
  ```

4. 画面が立ち上がれば成功です。

### ROS2 を使う場合

ROS2 を使う版は、別途 ROS2 のインストールが必要です。大抵のバージョンで動くと思いますが、少なくとも Humble と Lyrical は実機動作確認済みです。

インストール方法は環境ごとに若干異なるのでここでは省略します。まずは `ls /opt/ros` を実行して、ROS2 のディストリビューションが入っていれば大丈夫です。

ROS2 が入っている場合、たとえば Humble では次のように rosbridge サーバーを立てます。

```bash
source /opt/ros/humble/setup.bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

この状態で、別端末から `playground/open_duck_mini_v2/modified/mujoco_infer_ros2.py` を実行すると使えます。

```bash
uv run python playground/open_duck_mini_v2/modified/mujoco_infer_ros2.py
```

### ざっくり流れ

1.  `uv` を入れる (コマンド一つですぐできます)
2. `git clone` する
3. `uv sync` する
4. `playground/open_duck_mini_v2/mujoco_infer.py` を動かす
5. 成功

## 🙏 Acknowledgements

All credit for the original idea and implementation goes to the original author:

- **apirrone** — https://github.com/apirrone

If you find this project useful, please also consider supporting the original repository.

## 📄 License

This project follows the same license as the original repository unless otherwise specified.